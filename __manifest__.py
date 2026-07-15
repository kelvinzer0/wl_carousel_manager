# -*- coding: utf-8 -*-
{
    'name': 'Warung Lakku Carousel Manager',
    'version': '17.0.1.0.0',
    'summary': 'Carousel slide management with API key auth + OpenAPI PUT endpoint',
    'description': """
Warung Lakku Carousel Manager
==============================
Manage carousel/slider slides with separate desktop & mobile images.
Includes REST API with Bearer token auth (generate/revoke via backend)
and OpenAPI 3.0 spec served at /carousel/openapi.json.

Features:
  - Slide model: image_desktop, image_mobile, title, subtitle,
    link_url, cta_text, sequence, active, start_date, end_date
  - API key model: generate/revoke, scope (read/write/admin),
    last_used tracking, expiry
  - REST API: GET /carousel/api/slides, POST, PUT, DELETE
  - OpenAPI spec: /carousel/openapi.json
  - Backend UI: list/form views for slides + API keys
""",
    'author': 'Kelvin Yuli Andrian',
    'website': 'https://warunglakku.com',
    'license': 'LGPL-3',
    'depends': ['base', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/carousel_slide_views.xml',
        'views/carousel_api_key_views.xml',
        'views/menus.xml',
    ],
    'application': True,
    'installable': True,
}
