# Rytera global public URL

## Right now (no IP interstitial)

Cloudflare quick tunnel (random hostname, works worldwide):

See the active URL printed by `cloudflared tunnel --url http://127.0.0.1:18000`

## Named `https://app.rytera.ai` (recommended)

Requires your `rytera.ai` DNS in Cloudflare (free plan is fine):

```bash
brew install cloudflared
cloudflared tunnel login          # opens browser — pick rytera.ai zone
cloudflared tunnel create rytera
cloudflared tunnel route dns rytera app.rytera.ai
cloudflared tunnel run --url http://127.0.0.1:18000 rytera
```

Then open: **https://app.rytera.ai/dashboard**

## Why localtunnel asks for 24.62.239.117

Free `https://rytera.loca.lt` always shows an abuse gate and exposes your public IP. That is not a production global link.
