# -*- coding: utf-8 -*-
import json
import base64
import logging
from odoo import http, fields, _
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

SCOPE_LEVELS = {'read': 1, 'write': 2, 'admin': 3}


def _json_response(data, status=200):
    return Response(
        json.dumps(data, default=str),
        status=status,
        content_type='application/json',
        headers=[
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Authorization, Content-Type'),
        ],
    )


def _error(message, status=400, code=None):
    return _json_response({'error': message, 'code': code or status}, status)


def _authenticate(required_scope='read'):
    auth_header = request.httprequest.headers.get('Authorization', '')
    if not auth_header:
        return None, _error('Missing Authorization header', 401)
    key = auth_header.replace('Bearer ', '').strip()
    if not key:
        return None, _error('Empty API key', 401)
    api_key = request.env['carousel.api.key'].sudo().validate_key(
        key, required_scope=required_scope
    )
    if not api_key:
        return None, _error('Invalid or expired API key', 401)
    return api_key, None


def _slide_to_dict(slide):
    """Serialize wl.splide.slide to API dict.
    
    Maps wl.splide.slide fields to API-friendly names:
      name → title
      desktop_media → image_desktop (base64)
      mobile_media → image_mobile (base64)
    """
    base_url = request.env['ir.config_parameter'].sudo().get_param(
        'web.base.url', '')
    return {
        'id': slide.id,
        'title': slide.name or '',
        'link_url': slide.link_url or '',
        'link_new_tab': slide.link_new_tab,
        'sequence': slide.sequence,
        'active': slide.active,
        'image_desktop_url': f'{base_url}{slide.desktop_media_url}' if slide.desktop_media_url else '',
        'image_mobile_url': f'{base_url}{slide.mobile_media_url}' if slide.mobile_media_url else '',
        'desktop_media_type': slide.desktop_media_type or 'image',
        'mobile_media_type': slide.mobile_media_type or 'image',
        'desktop_media_filename': slide.desktop_media_filename or '',
        'mobile_media_filename': slide.mobile_media_filename or '',
        'create_date': slide.create_date.isoformat() if slide.create_date else None,
        'write_date': slide.write_date.isoformat() if slide.write_date else None,
    }


class CarouselAPI(http.Controller):
    """REST API for wl.splide.slide management."""

    # ================================================================
    # OPTIONS (CORS preflight)
    # ================================================================
    @http.route('/carousel/api/slides', type='http', auth='public',
                methods=['OPTIONS'], csrf=False)
    def slides_options(self, **kw):
        return Response(status=204, headers=[
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Authorization, Content-Type'),
        ])

    # ================================================================
    # GET /carousel/api/slides — list all slides
    # ================================================================
    @http.route('/carousel/api/slides', type='http', auth='public',
                methods=['GET'], csrf=False)
    def slides_list(self, **kw):
        api_key, err = _authenticate('read')
        if err:
            return err

        only_active = kw.get('active') == 'true'
        domain = []
        if only_active:
            domain = [('active', '=', True)]

        slides = request.env['wl.splide.slide'].sudo().search(domain)
        return _json_response({
            'count': len(slides),
            'slides': [_slide_to_dict(s) for s in slides],
        })

    # ================================================================
    # GET /carousel/api/slides/<id> — get single slide
    # ================================================================
    @http.route('/carousel/api/slides/<int:slide_id>', type='http',
                auth='public', methods=['GET'], csrf=False)
    def slides_get(self, slide_id, **kw):
        api_key, err = _authenticate('read')
        if err:
            return err

        slide = request.env['wl.splide.slide'].sudo().browse(slide_id)
        if not slide.exists():
            return _error('Slide not found', 404)

        return _json_response(_slide_to_dict(slide))

    # ================================================================
    # POST /carousel/api/slides — create new slide
    # ================================================================
    @http.route('/carousel/api/slides', type='http', auth='public',
                methods=['POST'], csrf=False)
    def slides_create(self, **kw):
        api_key, err = _authenticate('write')
        if err:
            return err

        try:
            body = json.loads(request.httprequest.data)
        except (json.JSONDecodeError, ValueError):
            return _error('Invalid JSON body', 400)

        if not body.get('title'):
            return _error('Field "title" is required', 400)
        if not body.get('image_desktop'):
            return _error('Field "image_desktop" is required (base64 string)', 400)
        if not body.get('image_mobile'):
            return _error('Field "image_mobile" is required (base64 string)', 400)

        # Map API fields → wl.splide.slide fields
        vals = {
            'name': body['title'],
            'desktop_media': body['image_desktop'],
            'mobile_media': body['image_mobile'],
            'desktop_media_filename': body.get('desktop_media_filename', 'desktop.jpg'),
            'mobile_media_filename': body.get('mobile_media_filename', 'mobile.jpg'),
            'link_url': body.get('link_url', ''),
            'link_new_tab': body.get('link_new_tab', True),
            'sequence': body.get('sequence', 10),
            'active': body.get('active', True),
        }

        slide = request.env['wl.splide.slide'].sudo().create(vals)
        _logger.info('Slide created via API: id=%d name=%s by key=%s',
                     slide.id, slide.name, api_key.name)
        return _json_response(_slide_to_dict(slide), 201)

    # ================================================================
    # PUT /carousel/api/slides/<id> — update slide (mobile & desktop)
    # ================================================================
    @http.route('/carousel/api/slides/<int:slide_id>', type='http',
                auth='public', methods=['PUT'], csrf=False)
    def slides_update(self, slide_id, **kw):
        api_key, err = _authenticate('write')
        if err:
            return err

        slide = request.env['wl.splide.slide'].sudo().browse(slide_id)
        if not slide.exists():
            return _error('Slide not found', 404)

        try:
            body = json.loads(request.httprequest.data)
        except (json.JSONDecodeError, ValueError):
            return _error('Invalid JSON body', 400)

        # Map API fields → wl.splide.slide fields
        field_map = {
            'title': 'name',
            'image_desktop': 'desktop_media',
            'image_mobile': 'mobile_media',
            'desktop_media_filename': 'desktop_media_filename',
            'mobile_media_filename': 'mobile_media_filename',
            'link_url': 'link_url',
            'link_new_tab': 'link_new_tab',
            'sequence': 'sequence',
            'active': 'active',
        }

        vals = {}
        for api_field, model_field in field_map.items():
            if api_field in body:
                vals[model_field] = body[api_field]

        if not vals:
            return _error('No fields to update', 400)

        slide.sudo().write(vals)
        _logger.info('Slide updated via API: id=%d fields=%s by key=%s',
                     slide.id, list(vals.keys()), api_key.name)
        return _json_response(_slide_to_dict(slide))

    # ================================================================
    # DELETE /carousel/api/slides/<id> — delete slide
    # ================================================================
    @http.route('/carousel/api/slides/<int:slide_id>', type='http',
                auth='public', methods=['DELETE'], csrf=False)
    def slides_delete(self, slide_id, **kw):
        api_key, err = _authenticate('write')
        if err:
            return err

        slide = request.env['wl.splide.slide'].sudo().browse(slide_id)
        if not slide.exists():
            return _error('Slide not found', 404)

        name = slide.name
        slide.sudo().unlink()
        _logger.info('Slide deleted via API: id=%d name=%s by key=%s',
                     slide_id, name, api_key.name)
        return _json_response({'deleted': True, 'id': slide_id})

    # ================================================================
    # POST /carousel/api/keys — generate new API key (admin only)
    # ================================================================
    @http.route('/carousel/api/keys', type='http', auth='public',
                methods=['POST'], csrf=False)
    def keys_generate(self, **kw):
        api_key, err = _authenticate('admin')
        if err:
            return err

        try:
            body = json.loads(request.httprequest.data)
        except (json.JSONDecodeError, ValueError):
            return _error('Invalid JSON body', 400)

        if not body.get('name'):
            return _error('Field "name" is required', 400)

        record, key_string = request.env['carousel.api.key'].sudo().generate_key(
            name=body['name'],
            scope=body.get('scope', 'write'),
            expires_at=body.get('expires_at'),
        )

        result = record.to_dict()
        result['key'] = key_string
        _logger.info('API key generated via API: %s by key=%s',
                     record.name, api_key.name)
        return _json_response(result, 201)

    # ================================================================
    # DELETE /carousel/api/keys/<id> — revoke API key (admin only)
    # ================================================================
    @http.route('/carousel/api/keys/<int:key_id>', type='http',
                auth='public', methods=['DELETE'], csrf=False)
    def keys_revoke(self, key_id, **kw):
        api_key, err = _authenticate('admin')
        if err:
            return err

        target = request.env['carousel.api.key'].sudo().browse(key_id)
        if not target.exists():
            return _error('API key not found', 404)

        target.sudo().revoke()
        _logger.info('API key revoked via API: %s by key=%s',
                     target.name, api_key.name)
        return _json_response({'revoked': True, 'id': key_id})

    # ================================================================
    # GET /carousel/api/keys — list all API keys (admin only)
    # ================================================================
    @http.route('/carousel/api/keys', type='http', auth='public',
                methods=['GET'], csrf=False)
    def keys_list(self, **kw):
        api_key, err = _authenticate('admin')
        if err:
            return err

        keys = request.env['carousel.api.key'].sudo().search([])
        return _json_response({
            'count': len(keys),
            'keys': [k.to_dict() for k in keys],
        })
