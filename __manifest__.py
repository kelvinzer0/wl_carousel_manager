# -*- coding: utf-8 -*-
{
    'name': 'Warung Lakku Carousel Manager',
    'version': '17.0.1.1.0',
    'summary': 'REST API + API key management for wl_splide_carousel slides',
    'description': """
Warung Lakku Carousel Manager
==============================
REST API layer for managing wl.splide.slide records via Bearer token auth.
Extends the existing wl_splide_carousel module — no duplicate models.

Features:
  - API key model: generate/revoke, scope (read/write/admin),
    last_used tracking, expiry
  - REST API: GET/POST/PUT/DELETE /carousel/api/slides
  - OpenAPI 3.0 spec served at /carousel/openapi.json
  - Backend UI: API Keys management (Slides managed by wl_splide_carousel)

Depends on: wl_splide_carousel (provides wl.splide.slide model + frontend rendering)
""",
    'author': 'Kelvin Yuli Andrian',
    'website': 'https://warunglakku.com',
    'license': 'LGPL-3',
    'depends': ['base', 'website', 'wl_splide_carousel'],
    'data': [
        'security/ir.model.access.csv',
        'views/carousel_api_key_views.xml',
        'views/menus.xml',
    ],
    'application': True,
    'installable': True,
}
