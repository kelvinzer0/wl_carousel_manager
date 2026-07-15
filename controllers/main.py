# -*- coding: utf-8 -*-
import json
import base64
import logging
from odoo import http, fields, _
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

# Scope hierarchy for permission checks
SCOPE_LEVELS = {'read': 1, 'write': 2, 'admin': 3}


def _json_response(data, status=200):
    """Helper: return JSON response with proper headers."""
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
    """Helper: return error JSON response."""
    return _json_response({'error': message, 'code': code or status}, status)


def _authenticate(required_scope='read'):
    """Authenticate request via Bearer token.
    
    Returns tuple: (api_key_record, error_response)
    If authentication succeeds, error_response is None.
    """
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


class CarouselAPI(http.Controller):
    """REST API for carousel slide management."""

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

        slides = request.env['carousel.slide'].sudo().search(domain)
        return _json_response({
            'count': len(slides),
            'slides': [s.to_dict() for s in slides],
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

        slide = request.env['carousel.slide'].sudo().browse(slide_id)
        if not slide.exists():
            return _error('Slide not found', 404)

        return _json_response(slide.to_dict())

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

        # Validate required fields
        if not body.get('title'):
            return _error('Field "title" is required', 400)
        if not body.get('image_desktop'):
            return _error('Field "image_desktop" is required (base64 string)', 400)

        # Build values
        vals = {
            'title': body['title'],
            'subtitle': body.get('subtitle', ''),
            'cta_text': body.get('cta_text', 'Pesan Sekarang'),
            'link_url': body.get('link_url', '/shop'),
            'image_desktop': body['image_desktop'],
            'image_mobile': body.get('image_mobile', False),
            'sequence': body.get('sequence', 10),
            'active': body.get('active', True),
            'start_date': body.get('start_date', False),
            'end_date': body.get('end_date', False),
            'api_key_id': api_key.id,
        }

        slide = request.env['carousel.slide'].sudo().create(vals)
        _logger.info('Slide created via API: id=%d title=%s by key=%s',
                     slide.id, slide.title, api_key.name)
        return _json_response(slide.to_dict(), 201)

    # ================================================================
    # PUT /carousel/api/slides/<id> — update slide (mobile & desktop)
    # ================================================================
    @http.route('/carousel/api/slides/<int:slide_id>', type='http',
                auth='public', methods=['PUT'], csrf=False)
    def slides_update(self, slide_id, **kw):
        api_key, err = _authenticate('write')
        if err:
            return err

        slide = request.env['carousel.slide'].sudo().browse(slide_id)
        if not slide.exists():
            return _error('Slide not found', 404)

        try:
            body = json.loads(request.httprequest.data)
        except (json.JSONDecodeError, ValueError):
            return _error('Invalid JSON body', 400)

        # Build update values — only update provided fields
        allowed_fields = [
            'title', 'subtitle', 'cta_text', 'link_url',
            'image_desktop', 'image_mobile',
            'sequence', 'active', 'start_date', 'end_date',
        ]
        vals = {}
        for field in allowed_fields:
            if field in body:
                vals[field] = body[field]

        if not vals:
            return _error('No fields to update', 400)

        vals['api_key_id'] = api_key.id
        slide.sudo().write(vals)
        _logger.info('Slide updated via API: id=%d fields=%s by key=%s',
                     slide.id, list(vals.keys()), api_key.name)
        return _json_response(slide.to_dict())

    # ================================================================
    # DELETE /carousel/api/slides/<id> — delete slide
    # ================================================================
    @http.route('/carousel/api/slides/<int:slide_id>', type='http',
                auth='public', methods=['DELETE'], csrf=False)
    def slides_delete(self, slide_id, **kw):
        api_key, err = _authenticate('write')
        if err:
            return err

        slide = request.env['carousel.slide'].sudo().browse(slide_id)
        if not slide.exists():
            return _error('Slide not found', 404)

        title = slide.title
        slide.sudo().unlink()
        _logger.info('Slide deleted via API: id=%d title=%s by key=%s',
                     slide_id, title, api_key.name)
        return _json_response({'deleted': True, 'id': slide_id})

    # ================================================================
    # GET /carousel/image/<id>/<variant> — serve slide image
    # ================================================================
    @http.route('/carousel/image/<int:slide_id>/<string:variant>', type='http',
                auth='public', methods=['GET'], csrf=False)
    def slide_image(self, slide_id, variant, **kw):
        """Serve slide image (desktop or mobile). Public, no auth needed."""
        slide = request.env['carousel.slide'].sudo().browse(slide_id)
        if not slide.exists():
            return _error('Slide not found', 404)

        if variant == 'desktop':
            image = slide.image_desktop
        elif variant == 'mobile':
            image = slide.image_mobile or slide.image_desktop  # fallback to desktop
        else:
            return _error('Invalid variant. Use "desktop" or "mobile".', 400)

        if not image:
            return _error('No image available', 404)

        # image is base64 string in Odoo
        image_data = base64.b64decode(image)
        return Response(image_data, status=200, content_type='image/jpeg',
                        headers=[('Cache-Control', 'public, max-age=3600')])

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
        result['key'] = key_string  # Only returned ONCE at creation
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
