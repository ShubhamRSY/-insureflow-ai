import sys,glob,os
from playwright.sync_api import sync_playwright
out,shots=sys.argv[1],sys.argv[2]
with sync_playwright() as p:
    b=p.chromium.launch(channel="chrome"); pg=b.new_page(viewport={"width":1200,"height":900})
    for f in sorted(glob.glob(os.path.join(shots,"*.html"))):
        pg.goto("file://"+f); pg.screenshot(path=os.path.join(out,os.path.basename(f)[:-5]+".png"),full_page=True)
    b.close()
