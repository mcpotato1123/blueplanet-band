/* Browser simulator for the band build — same data, same geometry, no Vela APIs. */
(function () {
  const A = window.XBY_ASSETS
  const S = window.XBY_STORY
  const VM = window.XBY_VM

  // ------------------------------------------------------------ layout (mirror of reader.js)
  const TEXT_BOX_W = 316, TEXT_PAD = 6, TEXT_BOX_H = 144, MAX_LINES = 6, TEXT_TOP = 338
  const BREAK_AFTER = '，。！？；：、）」』…—'
  let settings = { size: 20, speed: 28, autoMs: 0, fast: false }

  function layout() {
    const size = settings.size
    const lineH = size + 4
    return {
      size: size,
      lineH: lineH,
      cpl: Math.max(4, Math.floor((TEXT_BOX_W - TEXT_PAD) / size)),
      lpp: Math.max(1, Math.min(MAX_LINES, Math.floor(TEXT_BOX_H / lineH))),
    }
  }

  function wrapText(text, cpl) {
    const lines = []
    String(text || '').split('\n').forEach((raw) => {
      let s = raw
      if (s === '') { lines.push(''); return }
      while (s.length > cpl) {
        let cut = cpl
        const lo = Math.max(2, cpl - 8)
        for (let k = cpl; k > lo; k--) {
          if (BREAK_AFTER.indexOf(s.charAt(k - 1)) >= 0) { cut = k; break }
        }
        lines.push(s.slice(0, cut))
        s = s.slice(cut)
      }
      lines.push(s)
    })
    return lines.length ? lines : ['']
  }

  function paginate(text) {
    const L = layout()
    const lines = wrapText(text, L.cpl)
    if (!lines.length) return [['']]
    if (lines.length <= L.lpp) return [lines]
    // 均分：超出一页时两边行数差不多，别让第二页只剩一个短尾巴（同 reader.js）
    const pages = Math.ceil(lines.length / L.lpp)
    const per = Math.ceil(lines.length / pages)
    const out = []
    for (let i = 0; i < lines.length; i += per) {
      const chunk = lines.slice(i, i + per)
      const last = out.length ? out[out.length - 1] : null
      if (last && last.length + chunk.length <= L.lpp) out[out.length - 1] = last.concat(chunk)
      else out.push(chunk)
    }
    return out
  }

  // ------------------------------------------------------------ story source
  const readText = (path, cb) => {
    if (path.indexOf('index.txt') >= 0) return cb(null, JSON.stringify(S.index))
    const text = S.chunks[path]
    if (text === undefined) return cb('missing ' + path)
    cb(null, text)
  }

  const reader = VM.createReader(readText)
  const SLOT_LEFT = { l: 10, c: 60, r: 110 }
/* 同台人数决定立绘尺寸：1 人放大居中，2 人左右，3 人缩小并排 */
const SPRITE_SIZES = { 1: [200, 400, 80], 2: [168, 336, 144], 3: [110, 220, 260] }
  const $ = (id) => document.getElementById(id)

  let pages = [['']], pageIdx = 0, pageText = '', typing = 0, typingToken = 0
  let typingTimer = null, autoTimer = null, bgTimer = null, bgOffset = 0, bgDir = 1
  let cgTimer = null, cgOffset = 0, cgDir = 1, cgWide = 853, cgKey = ''
  let choices = [], menuOpen = false, ended = false, history = []
  let running = false

  // ------------------------------------------------------------ rendering
  function setStage(st) {
    const hasBg = st.bg && st.bg !== 'black'
    $('solid').style.display = hasBg ? 'none' : 'block'
    $('bg').style.display = hasBg ? 'block' : 'none'
    if (hasBg) {
      const src = A.bgPath(st.bg)
      if ($('bg').getAttribute('src') !== src) $('bg').setAttribute('src', src)
      if (!bgTimer) startPan()
    } else {
      stopPan()
    }
    const cgSrc = st.fg ? A.cgPath(st.fg) : ''
    $('cg').style.display = cgSrc ? 'block' : 'none'
    if (cgSrc) {
      $('cg').setAttribute('src', cgSrc)
      if (st.fg !== cgKey) {
        cgKey = st.fg
        cgWide = (A.CG_WIDE && A.CG_WIDE[st.fg]) || 853
        cgOffset = 0
        cgDir = 1
        $('cg').style.width = cgWide + 'px'
        $('cg').style.height = '480px'
        $('cg').style.objectFit = 'fill'
        $('cg').style.left = '0px'
        stopCgPan()
      }
      if (!cgTimer) startCgPan()
    } else {
      cgKey = ''
      stopCgPan()
    }

    const slots = VM.slotChars(st.chars)
    const order = []
    if (slots.l) order.push('L')
    if (slots.c) order.push('C')
    if (slots.r) order.push('R')
    const cast = order.length
    paint('L', slots.l, cast, order.indexOf('L'))
    paint('C', slots.c, cast, order.indexOf('C'))
    paint('R', slots.r, cast, order.indexOf('R'))
  }

  function paint(slot, ch, cast, slotIndex) {
    const base = $('sp' + slot), face = $('sp' + slot + 'f'), flush = $('sp' + slot + 'b')
    if (!ch) {
      base.style.display = 'none'; face.style.display = 'none'; flush.style.display = 'none'
      return
    }
    const spec = SPRITE_SIZES[Math.min(3, Math.max(1, cast || 1))] || SPRITE_SIZES[3]
    const sw = spec[0], sh = spec[1], stop = spec[2]
    let left = 0
    if (cast <= 1) left = Math.round((336 - sw) / 2)
    else if (cast === 2) left = slotIndex === 0 ? 0 : 336 - sw
    else left = slotIndex === 0 ? 2 : (slotIndex === 1 ? Math.round((336 - sw) / 2) : 336 - sw - 2)
    const k = sw / 210
    let pose
    if (ch.tag === 'dianzhang') {
      pose = A.spritePath(ch.tag, (ch.extra || '').indexOf('speak') >= 0 ? 'pose2.png' : 'pose1.png')
      base.src = pose
      base.style.left = left + 'px'; base.style.top = stop + 'px'
      base.style.width = sw + 'px'; base.style.height = sh + 'px'
      base.style.display = 'block'
      face.style.display = 'none'; flush.style.display = 'none'
      return
    }
    base.src = A.spritePath(ch.tag, 'base.png')
    base.style.left = left + 'px'; base.style.top = stop + 'px'
    base.style.width = sw + 'px'; base.style.height = sh + 'px'
    base.style.display = 'block'

    const ex = (ch.extra || '').split(',').filter(function (x) { return !!x }).join('_')
    const fname = 'face__' + (ch.eye || '-') + '__' + (ch.brow || '-') + '__' + (ch.mouth || '-') + '__' + (ex || '-') + '.png'
    const meta = A.SPRITES[ch.tag + '__meta']
    if (A.hasSprite(ch.tag, fname) && meta) {
      face.src = A.spritePath(ch.tag, fname)
      face.style.left = Math.round(left + meta.face[0] * k) + 'px'
      face.style.top = Math.round(stop + meta.face[1] * k) + 'px'
      face.style.width = Math.round((meta.face[2] - meta.face[0]) * k) + 'px'
      face.style.height = Math.round((meta.face[3] - meta.face[1]) * k) + 'px'
      face.style.display = 'block'
    } else {
      face.style.display = 'none'
    }
    if ((ch.extra || '').indexOf('flush') >= 0 && A.hasSprite(ch.tag, 'flush.png')) {
      flush.src = A.spritePath(ch.tag, 'flush.png')
      flush.style.left = left + 'px'; flush.style.top = stop + 'px'
      flush.style.width = sw + 'px'; flush.style.height = sh + 'px'
      flush.style.display = 'block'
    } else {
      flush.style.display = 'none'
    }
  }

  function renderHud(st) {
    $('hudT').textContent = st.chapterTitle || '——'
    $('hudD').textContent = st.date || ''
    const chs = reader.index.chapters
    let i = 0
    for (; i < chs.length; i++) {
      const end = chs[i + 1] ? chs[i + 1].start : reader.index.total
      if (st.pc >= chs[i].start && st.pc < end) break
    }
    const ch = chs[Math.min(i, chs.length - 1)]
    const next = chs[i + 1]
    const span = Math.max(1, (next ? next.start : reader.index.total) - ch.start)
    $('menuSub').textContent = (st.chapterTitle || '') + ' · ' +
      Math.min(99, Math.round((st.pc - ch.start) * 100 / span)) + '%'
  }

  function renderLines(showed) {
    const seg = String(showed).split('\n')
    const L = layout()
    for (let i = 0; i < 6; i++) {
      const el = $('l' + i)
      el.textContent = seg[i] || ''
      el.style.top = (TEXT_TOP + i * L.lineH) + 'px'
      el.style.fontSize = L.size + 'px'
      el.style.lineHeight = L.lineH + 'px'
    }
  }

  function playPage() {
    clearAuto()
    pageText = (pages[pageIdx] || ['']).join('\n')
    typing = 0
    renderLines('')
    $('more').style.display = 'none'
    const speed = settings.fast ? 0 : settings.speed
    if (!speed) { finishTyping(); return }
    typingToken++
    const token = typingToken
    const started = Date.now()
    const tick = () => {
      if (token !== typingToken) return
      const n = Math.max(typing + 1, Math.floor((Date.now() - started) / speed) + 1)
      if (n >= pageText.length) { typing = pageText.length; renderLines(pageText); finishTyping(); return }
      typing = n
      renderLines(pageText.slice(0, n))
      typingTimer = setTimeout(tick, 50)
    }
    tick()
  }

  function finishTyping() {
    typingToken++
    if (typingTimer) { clearTimeout(typingTimer); typingTimer = null }
    typing = pageText.length
    renderLines(pageText)
    $('more').style.display = choices.length || ended ? 'none' : 'block'
    scheduleAuto()
  }

  function clearAuto() { if (autoTimer) { clearTimeout(autoTimer); autoTimer = null } }

  function scheduleAuto() {
    clearAuto()
    if (choices.length || ended || menuOpen) return
    if (settings.fast) { autoTimer = setTimeout(advance, 220); return }
    if (!settings.autoMs) return
    const n = pageText.replace(/\s/g, '').length
    const wait = Math.max(1200, Math.min(12000, Math.round(700 + n * settings.autoMs)))
    autoTimer = setTimeout(advance, wait)
  }

  function onFrame(frame) {
    if (!frame) return
    if (frame.kind === 'menu') { showChoices(frame.options); return }
    if (frame.kind === 'end') {
      ended = true
      $('ending').style.display = 'flex'
      $('more').style.display = 'none'
      $('choices').innerHTML = ''
      choices = []
      return
    }
    ended = false
    $('ending').style.display = 'none'
    const st = reader.state
    setStage(st)
    renderHud(st)
    $('name').textContent = frame.who || ''
    $('name').style.display = frame.who ? 'block' : 'none'
    $('panel').style.display = 'block'
    pages = paginate(frame.text)
    pageIdx = 0
    history.push(reader.snapshot())
    if (history.length > 60) history.shift()
    playPage()
  }

  function showChoices(options) {
    choices = options
    const box = $('choices')
    box.innerHTML = ''
    options.forEach((opt, i) => {
      const el = document.createElement('div')
      el.className = 'choice'
      el.textContent = opt.text
      el.addEventListener('click', (ev) => {
        ev.stopPropagation()
        if (!choices.length) return
        choices = []
        box.innerHTML = ''
        reader.choose(i, (err, frame) => { if (!err) onFrame(frame) })
      })
      box.appendChild(el)
    })
    $('more').style.display = 'none'
  }

  function advance() {
    if (menuOpen || choices.length) return
    if (ended) { showTitle(); return }
    if (typing < pageText.length) { finishTyping(); return }
    if (pageIdx < pages.length - 1) { pageIdx++; playPage(); return }
    reader.next((err, frame) => { if (!err) onFrame(frame) })
  }

  // ------------------------------------------------------------ background pan
  function startPan() {
    if (bgTimer) return
    bgOffset = 0; bgDir = 1
    bgTimer = setInterval(() => {
      if (menuOpen || ended) return
      bgOffset += 4 * bgDir
      if (bgOffset >= 336) { bgOffset = 336; bgDir = -1 }
      if (bgOffset <= 0) { bgOffset = 0; bgDir = 1 }
      $('bg').style.left = '-' + bgOffset + 'px'
    }, 100)
  }
  function stopPan() { if (bgTimer) { clearInterval(bgTimer); bgTimer = null } }
  function startCgPan() {
    if (cgTimer) return
    cgTimer = setInterval(() => {
      if (menuOpen || ended) return
      cgOffset += 4 * cgDir
      const max = Math.max(0, cgWide - 336)
      if (cgOffset >= max) { cgOffset = max; cgDir = -1 }
      if (cgOffset <= 0) { cgOffset = 0; cgDir = 1 }
      $('cg').style.left = '-' + cgOffset + 'px'
    }, 100)
  }
  function stopCgPan() { if (cgTimer) { clearInterval(cgTimer); cgTimer = null } }

  // ------------------------------------------------------------ screens
  function showTitle() {
    running = false
    stopPan()
    stopCgPan()
    $('titleScr').style.display = 'block'
    $('chapScr').style.display = 'none'
    $('menu').style.display = 'none'
    $('ending').style.display = 'none'
    $('titleBg').src = '../src/common/img/ui/title_bg.png'
    menuOpen = false
    $('resumeLine').textContent = '从序章开始阅读 · 共 ' + reader.index.chapters.length + ' 章'
  }

  function startGame(chapterId) {
    $('titleScr').style.display = 'none'
    $('chapScr').style.display = 'none'
    running = true
    ended = false
    history = []
    reader.start(chapterId || 'ep1', (err, frame) => { if (!err) onFrame(frame) })
  }

  function showChapters() {
    const box = $('chapScr')
    box.innerHTML = '<h3>章节选择</h3>'
    reader.index.chapters.forEach((c, i) => {
      const row = document.createElement('div')
      row.className = 'row'
      row.innerHTML = '<em>' + (i + 1) + '</em><span>' + c.title + '</span>'
      row.addEventListener('click', (ev) => { ev.stopPropagation(); startGame(c.id) })
      box.appendChild(row)
    })
    box.style.display = 'block'
    $('titleScr').style.display = 'none'
  }

  function toggleMenu(open) {
    menuOpen = open
    $('menu').style.display = open ? 'flex' : 'none'
    if (open) { clearAuto(); finishTyping() } else { scheduleAuto() }
  }

  // ------------------------------------------------------------ input
  let touchY = 0, touchT = 0, lockTap = 0

  $('stage').addEventListener('click', (ev) => {
    if (Date.now() - lockTap < 400) return
    lockTap = Date.now()
    if (ev.target.classList.contains('mbtn')) return
    if (!running) return
    if (ended) { showTitle(); return }
    advance()
  })

  document.querySelectorAll('[data-act]').forEach((el) => {
    el.addEventListener('click', (ev) => {
      ev.stopPropagation()
      const act = el.getAttribute('data-act')
      if (Date.now() - lockTap < 300) return
      lockTap = Date.now()
      if (act === 'start') return startGame('ep1')
      if (act === 'chapters') return showChapters()
      if (act === 'about') { alert('《海蓝星之梦》手环版模拟器\n素材与剧本来自 PC 版解包，仅供学习交流。'); return }
      if (act === 'close') return toggleMenu(false)
      if (act === 'auto') { settings.autoMs = settings.autoMs ? 0 : 90; scheduleAuto(); return }
      if (act === 'fast') { settings.fast = !settings.fast; scheduleAuto(); return advance() }
      if (act === 'rewind') {
        if (history.length < 2) return
        history.pop()
        const prev = history.pop()
        history.push(prev)
        toggleMenu(false)
        reader.resume(prev, (err, frame) => { if (!err) onFrame(frame) })
        return
      }
      if (act === 'size') { settings.size = settings.size >= 28 ? 14 : settings.size + 2; return }
      if (act === 'home') { toggleMenu(false); return showTitle() }
      if (act === 'exit') {
        window.close()
        setTimeout(() => { if (!window.closed) alert('浏览器里无法真正退出快应用\n真机上 this.$app.exit() 会直接关闭。') }, 120)
        return
      }
    })
  })

  $('stage').addEventListener('touchstart', (e) => {
    const t = e.touches[0]
    touchY = t.clientY; touchT = Date.now()
  }, { passive: true })

  $('stage').addEventListener('touchend', (e) => {
    if (Date.now() - touchT > 800) return
    const t = e.changedTouches[0]
    if (t.clientY - touchY > 36 && running && !menuOpen) { lockTap = Date.now(); toggleMenu(true) }
  }, { passive: true })

  // ------------------------------------------------------------ boot
  reader.init((err) => {
    if (err) { alert('剧本加载失败: ' + err); return }
    showTitle()
  })

  // debug hook (used by tools/sim_smoke.js and handy in the console)
  window.XBY_DEBUG = {
    reader: reader,
    start: startGame,
    advance: advance,
    chapters: showChapters,
    title: showTitle,
    state: () => reader.state,
    frame: () => reader.frame,
  }
})()
