import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

const VERSION = '0.7.0'

const ECG_POINTS: [number, number][] = [
  [0, 16], [14, 16], [16, 14], [18, 18], [20, 3], [22, 26],
  [24, 16], [30, 16], [36, 11], [42, 16], [64, 16],
]

function ecgY(x: number, offset: number): number {
  const pos = ((x + offset) % 64 + 64) % 64
  for (let i = 0; i < ECG_POINTS.length - 1; i++) {
    const [x0, y0] = ECG_POINTS[i]
    const [x1, y1] = ECG_POINTS[i + 1]
    if (pos >= x0 && pos <= x1) {
      return y0 + ((pos - x0) / (x1 - x0)) * (y1 - y0)
    }
  }
  return 16
}

function startAnimatedFavicon() {
  if (!import.meta.client) return () => {}

  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = 32
  const ctx = canvas.getContext('2d')
  if (!ctx) return () => {}

  let link = document.querySelector<HTMLLinkElement>("link[rel='icon'], link[rel='shortcut icon']")
  if (!link) {
    link = document.createElement('link')
    link.rel = 'icon'
    document.head.appendChild(link)
  }

  let offset = 0
  const timer = window.setInterval(() => {
    ctx.clearRect(0, 0, 32, 32)
    ctx.fillStyle = '#0a0a0a'
    ctx.fillRect(0, 0, 32, 32)
    ctx.shadowColor = '#E53E3E'
    ctx.shadowBlur = 3
    ctx.strokeStyle = '#E53E3E'
    ctx.lineWidth = 1.5
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.beginPath()
    for (let x = 0; x <= 32; x++) {
      const y = ecgY(x, offset)
      if (x === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    }
    ctx.stroke()
    link!.href = canvas.toDataURL('image/png')
    offset = (offset + 1) % 64
  }, 50)

  return () => clearInterval(timer)
}

export function usePresentationGsap() {
  let stopFavicon: (() => void) | undefined

  onMounted(async () => {
    if (!import.meta.client) return

    gsap.registerPlugin(ScrollTrigger)
    stopFavicon = startAnimatedFavicon()

    const hero = document.getElementById('hero')
    if (!hero) return

    const decor = hero.querySelectorAll('.absolute.inset-0.pointer-events-none > div')
    const badge = hero.querySelector('p.font-mono.text-indb-red')
    const subtitle = hero.querySelector('p.font-sans.font-light')
    const tagline = hero.querySelector('p.font-mono.text-indb-red\\/80')
    const pipeline = hero.querySelectorAll('.opacity-0.flex.gap-4')
    const cta = hero.querySelector('.mt-12.flex')

    const tl = gsap.timeline({ defaults: { ease: 'power2.inOut' } })

    if (decor[0]) tl.from(decor[0], { x: '120%', duration: 1.4 }, 0)
    if (decor[1]) tl.from(decor[1], { scale: 0.5, opacity: 0, duration: 1.8 }, 0.1)
    if (decor[2]) tl.from(decor[2], { scaleY: 0, duration: 1.4, transformOrigin: 'top' }, 0.2)
    if (decor[3]) tl.from(decor[3], { scaleX: 0, duration: 1.2, transformOrigin: 'left' }, 0.35)
    if (decor[4]) tl.from(decor[4], { y: 40, opacity: 0, rotation: 8, duration: 1.2 }, 0.4)

    if (badge) tl.fromTo(badge, { y: 12, opacity: 0 }, { y: 0, opacity: 1, duration: 1 }, 0.35)
    if (subtitle) tl.fromTo(subtitle, { y: 16, opacity: 0 }, { y: 0, opacity: 1, duration: 1 }, 0.5)
    if (tagline) tl.fromTo(tagline, { y: 10, opacity: 0 }, { y: 0, opacity: 1, duration: 0.9 }, 0.6)

    pipeline.forEach((el, i) => {
      tl.fromTo(el, { y: 8, opacity: 0 }, { y: 0, opacity: 1, duration: 0.85 }, 0.7 + i * 0.1)
    })
    if (cta) tl.fromTo(cta, { y: 10, opacity: 0 }, { y: 0, opacity: 1, duration: 0.85 }, 0.8)

    if (decor[1]) {
      gsap.to(decor[1], { rotation: 360, duration: 80, repeat: -1, ease: 'none', transformOrigin: 'center center' })
      gsap.to(decor[1], { x: 18, y: -14, duration: 30, repeat: -1, yoyo: true, ease: 'sine.inOut' })
    }
    if (decor[0]) gsap.to(decor[0], { x: -28, y: 22, scale: 1.04, duration: 22, repeat: -1, yoyo: true, ease: 'sine.inOut' })
    if (decor[2]) gsap.to(decor[2], { rotation: '+=4', x: -12, duration: 18, repeat: -1, yoyo: true, ease: 'sine.inOut', transformOrigin: 'top center' })
    if (decor[3]) gsap.to(decor[3], { y: -18, scaleX: 0.92, duration: 25, repeat: -1, yoyo: true, ease: 'sine.inOut' })
    if (decor[4]) gsap.to(decor[4], { x: 20, y: -15, rotation: 8, duration: 35, repeat: -1, yoyo: true, ease: 'sine.inOut' })

    const manifesto = document.querySelector('#philosophy')?.previousElementSibling
    if (manifesto) {
      ScrollTrigger.create({
        trigger: manifesto,
        start: 'top 80%',
        onEnter: () => {
          gsap.fromTo(manifesto, { y: 40, opacity: 0 }, { y: 0, opacity: 1, duration: 1, ease: 'power3.out' })
        },
        once: true,
      })
    }

    gsap.utils.toArray<HTMLElement>('.phase-block').forEach((el, i) => {
      ScrollTrigger.create({
        trigger: el,
        start: 'top 85%',
        onEnter: () => {
          gsap.fromTo(el, { y: 50, opacity: 0 }, { y: 0, opacity: 1, duration: 0.8, delay: i * 0.15, ease: 'power3.out' })
        },
        once: true,
      })
    })

    gsap.utils.toArray<HTMLElement>('.module-card').forEach((el, i) => {
      ScrollTrigger.create({
        trigger: el,
        start: 'top 90%',
        onEnter: () => {
          gsap.fromTo(
            el,
            { x: i % 2 === 0 ? -40 : 40, opacity: 0 },
            { x: 0, opacity: 1, duration: 0.7, delay: i * 0.1, ease: 'power2.out' },
          )
        },
        once: true,
      })
    })

    ;['#modularity', '#performance', '#signed-memory'].forEach((sel, i) => {
      const el = document.querySelector<HTMLElement>(sel)
      if (!el) return
      ScrollTrigger.create({
        trigger: el,
        start: 'top 90%',
        onEnter: () => {
          gsap.fromTo(el, { y: 30, opacity: 0 }, { y: 0, opacity: 1, duration: 0.7, delay: i * 0.15, ease: 'power2.out' })
        },
        once: true,
      })
    })

    gsap.utils.toArray<HTMLElement>('#use-cases .grid > div, #api .grid > div').forEach((el, i) => {
      ScrollTrigger.create({
        trigger: el,
        start: 'top 90%',
        onEnter: () => {
          gsap.fromTo(el, { scale: 0.92, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.6, delay: i * 0.07, ease: 'back.out(1.2)' })
        },
        once: true,
      })
    })
  })

  onUnmounted(() => {
    stopFavicon?.()
    ScrollTrigger.getAll().forEach((t) => t.kill())
  })

  return { version: VERSION }
}
