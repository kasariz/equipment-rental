import { Smartphone } from 'lucide-react'
import { useSyncExternalStore } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { canInstall, install, isIos, isStandalone, onInstallChange } from '@/lib/pwa'

/** Блок «Установить приложение» в профиле. В уже установленном приложении не показывается */
export function InstallApp() {
  const available = useSyncExternalStore(onInstallChange, canInstall, () => false)
  if (isStandalone()) return null

  return (
    <section className="mt-10 rounded-xl border border-line bg-paper p-5 sm:p-6">
      <h2 className="font-display flex items-center gap-2 text-lg font-semibold">
        <Smartphone className="size-5" aria-hidden />
        Приложение на телефон
      </h2>
      <p className="mt-2 max-w-prose text-steel">
        Сайт можно установить на главный экран: он будет открываться как приложение, с иконкой и без адресной строки.
      </p>
      {available ? (
        <Button
          className="mt-4"
          variant="dark"
          onClick={async () => {
            if (await install()) toast.success('Приложение установлено')
          }}
        >
          Установить приложение
        </Button>
      ) : isIos() ? (
        <p className="mt-3 text-sm">
          На iPhone: откройте сайт в Safari, нажмите «Поделиться» и выберите «На экран „Домой“».
        </p>
      ) : (
        <p className="mt-3 text-sm">
          Откройте меню браузера (⋮) и выберите «Установить приложение» или «Добавить на главный экран».
        </p>
      )}
    </section>
  )
}
