# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request, Response


class CarouselOpenAPI(http.Controller):
    """Serve OpenAPI 3.0 spec at /carousel/openapi.json."""

    @http.route('/carousel/openapi.json', type='http', auth='public',
                methods=['GET'], csrf=False)
    def openapi_spec(self, **kw):
        base_url = request.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', 'https://warunglakku.com')

        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": "Warung Lakku Carousel API",
                "description": "REST API for managing carousel slides (wl.splide.slide). "
                               "Supports separate desktop & mobile media, scheduling, "
                               "and ordering. \n\n"
                               "## Authentication\n"
                               "All endpoints require a Bearer token:\n"
                               "```\nAuthorization: Bearer wlc_xxxxxxxx\n```\n"
                               "Generate/revoke keys via Odoo backend or "
                               "POST /carousel/api/keys (admin scope).",
                "version": "1.1.0",
                "contact": {"name": "Warung Lakku", "url": "https://warunglakku.com"},
            },
            "servers": [{"url": base_url, "description": "Production"}],
            "components": {
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http", "scheme": "bearer",
                        "description": "API key prefixed with 'wlc_'.",
                    }
                },
                "schemas": {
                    "Slide": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "readOnly": True},
                            "title": {"type": "string", "example": "Promo Seblak",
                                       "description": "Internal slide label (maps to wl.splide.slide.name)"},
                            "image_desktop": {
                                "type": "string", "format": "byte",
                                "description": "Base64-encoded media for desktop (1920×960px, 2:1). Maps to desktop_media.",
                            },
                            "image_mobile": {
                                "type": "string", "format": "byte",
                                "description": "Base64-encoded media for mobile (800×1000px, 4:5). Maps to mobile_media.",
                            },
                            "desktop_media_filename": {"type": "string", "example": "banner-desktop.jpg"},
                            "mobile_media_filename": {"type": "string", "example": "banner-mobile.jpg"},
                            "link_url": {"type": "string", "example": "/shop?category=6"},
                            "link_new_tab": {"type": "boolean", "default": True},
                            "sequence": {"type": "integer", "default": 10},
                            "active": {"type": "boolean", "default": True},
                            "image_desktop_url": {"type": "string", "readOnly": True},
                            "image_mobile_url": {"type": "string", "readOnly": True},
                            "desktop_media_type": {"type": "string", "enum": ["image", "video"], "readOnly": True},
                            "mobile_media_type": {"type": "string", "enum": ["image", "video"], "readOnly": True},
                            "create_date": {"type": "string", "format": "date-time", "readOnly": True},
                            "write_date": {"type": "string", "format": "date-time", "readOnly": True},
                        },
                        "required": ["title", "image_desktop", "image_mobile"],
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
                        "properties": {"error": {"type": "string"}, "code": {"type": "integer"}},
                    },
                },
            },
            "security": [{"BearerAuth": []}],
            "paths": {
                "/carousel/api/slides": {
                    "get": {
                        "summary": "List all slides",
                        "security": [{"BearerAuth": []}],
                        "parameters": [
                            {"name": "active", "in": "query",
                             "schema": {"type": "string", "enum": ["true", "false"]}},
                        ],
                        "responses": {
                            "200": {"description": "List of slides",
                                    "content": {"application/json": {"schema": {
                                        "type": "object",
                                        "properties": {
                                            "count": {"type": "integer"},
                                            "slides": {"type": "array", "items": {"$ref": "#/components/schemas/Slide"}},
                                        },
                                    }}}},
                            "401": {"description": "Unauthorized"},
                        },
                    },
                    "post": {
                        "summary": "Create a new slide",
                        "security": [{"BearerAuth": []}],
                        "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Slide"}}}},
                        "responses": {
                            "201": {"description": "Slide created", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Slide"}}}},
                            "400": {"description": "Bad request"},
                            "401": {"description": "Unauthorized"},
                        },
                    },
                },
                "/carousel/api/slides/{slide_id}": {
                    "get": {
                        "summary": "Get a single slide by ID",
                        "security": [{"BearerAuth": []}],
                        "parameters": [{"name": "slide_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                        "responses": {
                            "200": {"description": "Slide details", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Slide"}}}},
                            "404": {"description": "Slide not found"},
                        },
                    },
                    "put": {
                        "summary": "Update a slide (mobile & desktop media)",
                        "description": "Update any field of an existing slide. Only provided fields are updated.",
                        "security": [{"BearerAuth": []}],
                        "parameters": [{"name": "slide_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "image_desktop": {"type": "string", "format": "byte", "description": "Base64 media for desktop"},
                                    "image_mobile": {"type": "string", "format": "byte", "description": "Base64 media for mobile"},
                                    "desktop_media_filename": {"type": "string"},
                                    "mobile_media_filename": {"type": "string"},
                                    "link_url": {"type": "string"},
                                    "link_new_tab": {"type": "boolean"},
                                    "sequence": {"type": "integer"},
                                    "active": {"type": "boolean"},
                                },
                            }}},
                        },
                        "responses": {
                            "200": {"description": "Slide updated", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Slide"}}}},
                            "400": {"description": "No fields to update"},
                            "404": {"description": "Slide not found"},
                            "401": {"description": "Unauthorized"},
                        },
                    },
                    "delete": {
                        "summary": "Delete a slide",
                        "security": [{"BearerAuth": []}],
                        "parameters": [{"name": "slide_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                        "responses": {"200": {"description": "Slide deleted"}, "404": {"description": "Slide not found"}},
                    },
                },
                "/carousel/api/keys": {
                    "get": {
                        "summary": "List all API keys (admin scope)",
                        "security": [{"BearerAuth": []}],
                        "responses": {"200": {"description": "List of API keys"}, "401": {"description": "Admin scope required"}},
                    },
                    "post": {
                        "summary": "Generate a new API key (admin scope)",
                        "security": [{"BearerAuth": []}],
                        "requestBody": {"required": True, "content": {"application/json": {"schema": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "example": "n8n workflow"},
                                "scope": {"type": "string", "enum": ["read", "write", "admin"], "default": "write"},
                                "expires_at": {"type": "string", "format": "date-time"},
                            },
                            "required": ["name"],
                        }}}},
                        "responses": {"201": {"description": "API key created — key returned once",
                                              "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiKey"}}}}},
                    },
                },
                "/carousel/api/keys/{key_id}": {
                    "delete": {
                        "summary": "Revoke an API key (admin scope)",
                        "security": [{"BearerAuth": []}],
                        "parameters": [{"name": "key_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                        "responses": {"200": {"description": "API key revoked"}, "404": {"description": "Key not found"}},
                    },
                },
            },
        }

        return Response(
            json.dumps(spec, indent=2), status=200, content_type='application/json',
            headers=[('Access-Control-Allow-Origin', '*'), ('Cache-Control', 'no-cache')],
        )
