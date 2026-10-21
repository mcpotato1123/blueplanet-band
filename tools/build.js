/* Build wrapper: static pre-checks, then `aiot build`, then verify the rpk.
 *
 * Why not call `aiot build` directly: aiot wipes dist/ on every run and, on
 * Windows, its cleanup of the temp project copy fails with EPERM even though
 * the rpk was produced. This wrapper clears dist/, runs the build, tolerates
 * that EPERM when the rpk exists, and prints a short content report.
 */
const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const release = process.argv.indexOf('release') >= 0
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'src/manifest.json'), 'utf8'))
const expect = path.join(root, 'dist',
  `${manifest.package}.${release ? 'release' : 'debug'}.${manifest.versionName}.rpk`)

function fail(msg) {
  console.error('[build] ' + msg)
  process.exit(1)
}

// ---------------------------------------------------------------- pre-checks
const pages = fs.readdirSync(path.join(root, 'src/pages'))
for (const dir of pages) {
  const file = path.join(root, 'src/pages', dir, dir + '.ux')
  if (!fs.existsSync(file)) continue
  const src = fs.readFileSync(file, 'utf8')
  const script = src.slice(src.indexOf('<script>'))
  if (/^\s*data\s*:/m.test(script)) {
    fail(`${dir}.ux 同时出现 data 与 protected（Vela 会直接崩）`)
  }
  if (/opacity\s*:/.test(src)) {
    console.warn(`[build] 警告：${dir}.ux 使用了 opacity，真机上可能渲染出横条纹`)
  }
}

const aboutSrc = fs.readFileSync(path.join(root, 'src/pages/about/about.ux'), 'utf8')
const shown = (aboutSrc.match(/const APP_VERSION = '([^']+)'/) || [])[1]
if (shown !== manifest.versionName) {
  fail(`about.ux 里的版本号 ${shown} 与 manifest 的 ${manifest.versionName} 不一致`)
}

const indexFile = path.join(root, 'src/common/story/index.txt')
// 立绘 meta 必须和模拟器/页面用的是同一份（换裁切窗口后忘了 build_sim 会导致五官错位）
{
  const metaFile = 'src/common/img/s/changxia/meta.json'
  const assetsFile = 'src/common/assets.js'
  if (fs.existsSync(metaFile) && fs.existsSync(assetsFile)) {
    const live = JSON.parse(fs.readFileSync(metaFile, 'utf8'))
    const src = fs.readFileSync(assetsFile, 'utf8')
    const m = src.match(/"changxia__meta":\s*(\{[^}]*\})/)
    if (m) {
      const baked = JSON.parse(m[1])
      if (JSON.stringify(baked.face) !== JSON.stringify(live.face)) {
        fail('assets.js 里的立绘元数据已过期，先跑 python tools/build_assets.py（或 npm run assets）')
      }
    }
  }
}

if (!fs.existsSync(indexFile)) fail('缺少 src/common/story/index.txt，先跑 npm run story')
const index = JSON.parse(fs.readFileSync(indexFile, 'utf8'))
let nodes = 0
for (const c of index.chunks) {
  const f = path.join(root, 'src/common/story/' + c.file.replace('/common/story/', ''))
  if (!fs.existsSync(f)) fail('缺少分块 ' + f)
  nodes += fs.readFileSync(f, 'utf8').split('\n').filter(Boolean).length
}
if (nodes !== index.total) fail(`分块节点数 ${nodes} 与 index.total ${index.total} 不一致`)
console.log(`[build] 剧本 ${index.chapters.length} 章 / ${index.total} 指令 / ${index.chunks.length} 块`)

// ---------------------------------------------------------------- build
fs.rmSync(path.join(root, 'dist'), { recursive: true, force: true })
try {
  execSync(release ? 'npx aiot release' : 'npx aiot build', { cwd: root, stdio: 'inherit' })
} catch (e) {
  if (!fs.existsSync(expect)) fail('aiot 构建失败：' + e.message)
  console.warn('[build] aiot 退出码非 0（Windows 临时目录清理的已知问题），但产物已生成')
}

if (!fs.existsSync(expect)) fail('没有找到产物 ' + expect)
const size = fs.statSync(expect).size
console.log(`[build] OK ${path.basename(expect)} ${(size / 1048576).toFixed(2)} MB`)
