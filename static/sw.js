// Service worker mínimo: só permite a instalação do PWA.
// Sem cache offline (o app depende de login/sessão/dados do banco em tempo real).
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => self.clients.claim());
self.addEventListener('fetch', e => {});
