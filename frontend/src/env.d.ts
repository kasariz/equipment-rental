interface ImportMetaEnv {
  /** Ключ продукта «JavaScript API» из Кабинета разработчика Яндекса */
  readonly VITE_YANDEX_MAPS_API_KEY?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
