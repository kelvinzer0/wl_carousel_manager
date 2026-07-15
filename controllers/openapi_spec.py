# -*- coding: utf-8 -*-
import json
import os
from odoo import http
from odoo.http import request, Response


class CarouselOpenAPI(http.Controller):
    """Serve OpenAPI 3.0 spec at /carousel/openapi.json."""

    @http.route('/carousel/openapi.json', type='http', auth='public',
                methods=['GET'], csrf=False)
    def openapi_spec(self, **kw):
        """Return OpenAPI 3.0 spec for the Carousel API."""
        base_url = request.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', 'https://warunglakku.com')

        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": "Warung Lakku Carousel API",
                "description": "REST API for managing carousel/slider slides. "
                               "Supports separate desktop & mobile images, "
                               "scheduling, and ordering. "
                               "\n\n## Authentication\n"
                               "All endpoints require a Bearer token:\n"
                               "```\nAuthorization: Bearer wlc_xxxxxxxx\n```\n"
                               "Generate/revoke keys via Odoo backend or "
                               "POST /carousel/api/keys (admin scope).",
                "version": "1.0.0",
                "contact": {
                    "name": "Warung Lakku",
                    "url": "https://warunglakku.com",
                },
            },
            "servers": [
                {"url": base_url, "description": "Production"},
            ],
            "components": {
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "description": "API key prefixed with 'wlc_'. "
                                       "Get via Odoo backend or POST /carousel/api/keys.",
                    }
                },
                "schemas": {
                    "Slide": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "readOnly": True},
                            "title": {"type": "string", "example": "Promo Seblak"},
                            "subtitle": {"type": "string", "example": "Diskon 20%"},
                            "cta_text": {"type": "string", "example": "Pesan Sekarang"},
                            "link_url": {"type": "string", "example": "/shop?category=6"},
                            "image_desktop": {
                                "type": "string", "format": "byte",
                                "description": "Base64-encoded JPEG (1920×600px)",
                            },
                            "image_mobile": {
                                "type": "string", "format": "byte",
                                "description": "Base64-encoded JPEG (750×800px). "
                                               "Optional — falls back to desktop.",
                            },
                            "sequence": {"type": "integer", "default": 10},
                            "active": {"type": "boolean", "default": True},
                            "start_date": {"type": "string", "format": "date-time", "nullable": True},
                            "end_date": {"type": "string", "format": "date-time", "nullable": True},
                            "is_visible": {"type": "boolean", "readOnly": True},
                            "image_desktop_url": {"type": "string", "readOnly": True},
                            "image_mobile_url": {"type": "string", "readOnly": True},
                            "create_date": {"type": "string", "format": "date-time", "readOnly": True},
                            "write_date": {"type": "string", "format": "date-time", "readOnly": True},
                        },
                        "required": ["title", "image_desktop"],
                    },
                    "ApiKey": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "readOnly": True},
                            "name": {"type": "string", "example": "n8n workflow"},
                            "scope": {"type": "string", "enum": ["read", "write", "admin"]},
                            "active": {"type": "boolean"},
                            "expires_at": {"type": "string", "format": "date-time", "nullable": True},
                            "last_used": {"type": "string", "format": "date-time", "nullable": True, "readOnly": True},
                            "use_count": {"type": "integer", "readOnly": True},
                            "key": {"type": "string", "description": "Only returned once at creation"},
                            "key_preview": {"type": "string", "readOnly": True},
                        },
                        "required": ["name"],
                    },
                    "Error": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string"},
                            "code": {"type": "integer"},
                        },
                    },
                },
            },
            "security": [{"BearerAuth": []}],
            "paths": {
                "/carousel/api/slides": {
                    "get": {
                        "summary": "List all slides",
                        "description": "Returns all carousel slides. Use ?active=true "
                                       "to filter only active slides.",
                        "security": [{"BearerAuth": []}],
                        "parameters": [
                            {
                                "name": "active",
                                "in": "query",
                                "schema": {"type": "string", "enum": ["true", "false"]},
                                "description": "Filter by active status",
                            },
                        ],
                        "responses": {
                            "200": {
                                "description": "List of slides",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "count": {"type": "integer"},
                                                "slides": {
                                                    "type": "array",
                                                    "items": {"$ref": "#/components/schemas/Slide"},
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                            "401": {"description": "Unauthorized — invalid API key"},
                        },
                    },
                    "post": {
                        "summary": "Create a new slide",
                        "security": [{"BearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Slide"},
                                },
                            },
                        },
                        "responses": {
                            "201": {
                                "description": "Slide created",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/Slide"},
                                    },
                                },
                            },
                            "400": {"description": "Bad request — missing required fields"},
                            "401": {"description": "Unauthorized — invalid or insufficient scope"},
                        },
                    },
                },
                "/carousel/api/slides/{slide_id}": {
                    "get": {
                        "summary": "Get a single slide by ID",
                        "security": [{"BearerAuth": []}],
                        "parameters": [
                            {"name": "slide_id", "in": "path", "required": True,
                             "schema": {"type": "integer"}},
                        ],
                        "responses": {
                            "200": {"description": "Slide details",
                                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Slide"}}}},
                            "404": {"description": "Slide not found"},
                        },
                    },
                    "put": {
                        "summary": "Update a slide (mobile & desktop images)",
                        "description": "Update any field of an existing slide. "
                                       "Only provided fields are updated. "
                                       "This is the primary endpoint for pushing "
                                       "new slide images from external systems "
                                       "(n8n, mobile app, etc.).",
                        "security": [{"BearerAuth": []}],
                        "parameters": [
                            {"name": "slide_id", "in": "path", "required": True,
                             "schema": {"type": "integer"}},
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "title": {"type": "string"},
                                            "subtitle": {"type": "string"},
                                            "cta_text": {"type": "string"},
                                            "link_url": {"type": "string"},
                                            "image_desktop": {"type": "string", "format": "byte",
                                                             "description": "Base64 JPEG for desktop (1920×600)"},
                                            "image_mobile": {"type": "string", "format": "byte",
                                                            "description": "Base64 JPEG for mobile (750×800)"},
                                            "sequence": {"type": "integer"},
                                            "active": {"type": "boolean"},
                                            "start_date": {"type": "string", "format": "date-time"},
                                            "end_date": {"type": "string", "format": "date-time"},
                                        },
                                    },
                                },
                            },
                        },
                        "responses": {
                            "200": {"description": "Slide updated",
                                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Slide"}}}},
                            "400": {"description": "No fields to update or invalid data"},
                            "404": {"description": "Slide not found"},
                            "401": {"description": "Unauthorized"},
                        },
                    },
                    "delete": {
                        "summary": "Delete a slide",
                        "security": [{"BearerAuth": []}],
                        "parameters": [
                            {"name": "slide_id", "in": "path", "required": True,
                             "schema": {"type": "integer"}},
                        ],
                        "responses": {
                            "200": {"description": "Slide deleted"},
                            "404": {"description": "Slide not found"},
                        },
                    },
                },
                "/carousel/api/keys": {
                    "get": {
                        "summary": "List all API keys (admin scope)",
                        "security": [{"BearerAuth": []}],
                        "responses": {
                            "200": {"description": "List of API keys (without actual key strings)"},
                            "401": {"description": "Unauthorized — admin scope required"},
                        },
                    },
                    "post": {
                        "summary": "Generate a new API key (admin scope)",
                        "security": [{"BearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string", "example": "n8n workflow"},
                                            "scope": {"type": "string", "enum": ["read", "write", "admin"], "default": "write"},
                                            "expires_at": {"type": "string", "format": "date-time"},
                                        },
                                        "required": ["name"],
                                    },
                                },
                            },
                        },
                        "responses": {
                            "201": {"description": "API key created — key string returned once",
                                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiKey"}}}},
                        },
                    },
                },
                "/carousel/api/keys/{key_id}": {
                    "delete": {
                        "summary": "Revoke an API key (admin scope)",
                        "security": [{"BearerAuth": []}],
                        "parameters": [
                            {"name": "key_id", "in": "path", "required": True,
                             "schema": {"type": "integer"}},
                        ],
                        "responses": {
                            "200": {"description": "API key revoked"},
                            "404": {"description": "Key not found"},
                        },
                    },
                },
                "/carousel/image/{slide_id}/{variant}": {
                    "get": {
                        "summary": "Get slide image (public, no auth)",
                        "description": "Serve the slide image. No authentication required. "
                                       "Variant can be 'desktop' or 'mobile'.",
                        "security": [],
                        "parameters": [
                            {"name": "slide_id", "in": "path", "required": True,
                             "schema": {"type": "integer"}},
                            {"name": "variant", "in": "path", "required": True,
                             "schema": {"type": "string", "enum": ["desktop", "mobile"]}},
                        ],
                        "responses": {
                            "200": {"description": "Image binary (JPEG)"},
                            "404": {"description": "Slide or image not found"},
                        },
                    },
                },
            },
        }

        return Response(
            json.dumps(spec, indent=2),
            status=200,
            content_type='application/json',
            headers=[
                ('Access-Control-Allow-Origin', '*'),
                ('Cache-Control', 'no-cache'),
            ],
        )
