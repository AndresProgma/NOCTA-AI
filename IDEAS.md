# Ideas para implementar en Nocta AI

---

## 1. Análisis de productos trending en Marketplaces

Detectar qué productos se están vendiendo mucho en marketplaces, útil para dropshippers y vendedores.

**Plataformas a cubrir:**
- Amazon — Best Sellers, Movers & Shakers, New Releases
- MercadoLibre — Más vendidos por categoría (LATAM)
- eBay — Trending items, sold listings
- AliExpress / Alibaba — Productos con alto volumen de órdenes (sourcing para dropshipping)
- Etsy — Trending en nichos handmade
- Shopee — Tendencias Asia / LATAM
- Walmart Marketplace — Best sellers USA
- Shein / Temu — Tendencias de moda y productos masivos de bajo costo

**Herramientas de referencia:** Jungle Scout, Helium 10, Zik Analytics, SaleHoo

**Output esperado:** producto + marketplace + volumen estimado de ventas + tendencia (subiendo/bajando) + precio promedio + margen potencial para reventa

---

## 2. TikTok viral cross-región

Pipeline que detecta videos que ya funcionaron bien en TikTok en otros países para replicarlos o adaptarlos antes de que lleguen al mercado local.

**Lógica:** los contenidos virales viajan entre países con delay. Quien replica primero captura la ola.

**Cómo funciona:**
- Scraping de TikTok trending por región (ya tenemos proxies por región)
- Comparar si ese contenido ya existe en el mercado objetivo
- Identificar la ventana de oportunidad

**Output esperado:** video + país de origen + métricas (views/likes/shares) + si ya hay réplicas locales + oportunidad estimada

**Útil para:** creadores de contenido, marcas que quieren adelantarse a tendencias

---
