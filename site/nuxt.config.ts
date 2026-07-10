export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  future: {
    compatibilityVersion: 4,
  },
  devtools: { enabled: false },
  modules: ['@nuxtjs/tailwindcss'],
  ssr: true,
  nitro: {
    preset: 'static',
  },
  app: {
    head: {
      title: 'INDB — Interpretational Database · Signed Cognitive Memory',
      meta: [
        {
          name: 'description',
          content:
            'Interpretational Database — memory where meaning is read, not filed. Epistemological engine with signed memory.',
        },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      ],
      link: [
        { rel: 'icon', href: '/favicon.ico' },
        {
          rel: 'preconnect',
          href: 'https://fonts.googleapis.com',
        },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=IBM+Plex+Sans:wght@300;400;700;900&display=swap',
        },
      ],
    },
  },
  css: ['~/assets/css/main.css'],
})
