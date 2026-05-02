import { mkdirSync, readFileSync, rmSync, writeFileSync, existsSync, cpSync } from 'node:fs'
import { join, resolve } from 'node:path'

const root = resolve(process.cwd())
const dist = join(root, 'dist')
const assetsDir = join(dist, 'assets')
mkdirSync(assetsDir, { recursive: true })

rmSync(join(assetsDir, 'styles.css'), { force: true })
rmSync(join(dist, 'index.html'), { force: true })

const css = [
  readFileSync(join(root, 'src', 'index.css'), 'utf8'),
  readFileSync(join(root, 'src', 'App.css'), 'utf8'),
].join('\n\n')
writeFileSync(join(assetsDir, 'styles.css'), css, 'utf8')
writeFileSync(join(assetsDir, 'App.css'), css, 'utf8')
writeFileSync(join(assetsDir, 'index.css'), css, 'utf8')

const html = `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>修仙数值模型</title>
    <link rel="stylesheet" href="/assets/styles.css" />
    <script type="importmap">
      {
        "imports": {
          "react": "https://esm.sh/react@18.3.1",
          "react/jsx-runtime": "https://esm.sh/react@18.3.1/jsx-runtime",
          "react-dom/client": "https://esm.sh/react-dom@18.3.1/client"
        }
      }
    </script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/assets/main.js"></script>
  </body>
</html>`
writeFileSync(join(dist, 'index.html'), html, 'utf8')

if (existsSync(join(root, 'public'))) {
  cpSync(join(root, 'public'), dist, { recursive: true, force: true })
}
