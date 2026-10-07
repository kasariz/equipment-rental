import * as AlertDialog from '@radix-ui/react-alert-dialog'
import { useState, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'

type Props = {
  trigger: ReactNode
  title: string
  confirmLabel: string
  onConfirm: (reason: string) => void
}

/** Отклонение заявки с необязательной причиной: клиент увидит её у себя в бронях */
export function RejectDialog({ trigger, title, confirmLabel, onConfirm }: Props) {
  const [reason, setReason] = useState('')
  return (
    <AlertDialog.Root onOpenChange={(open) => open && setReason('')}>
      <AlertDialog.Trigger asChild>{trigger}</AlertDialog.Trigger>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 z-[2000] bg-ink/50" />
        <AlertDialog.Content className="fixed top-1/2 left-1/2 z-[2001] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-paper p-6 shadow-xl">
          <AlertDialog.Title className="font-display text-lg font-semibold">{title}</AlertDialog.Title>
          <AlertDialog.Description className="mt-2 text-steel">
            Время освободится, и его смогут забронировать другие. Причину клиент увидит в своих бронях.
          </AlertDialog.Description>
          <label className="mt-4 flex flex-col gap-1.5 text-sm font-medium">
            Причина (необязательно)
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={500}
              placeholder="Например: техника на ремонте, не дозвонились"
              className="min-h-20 rounded-md border border-line bg-paper px-3 py-2 text-[15px] font-normal focus-visible:border-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal"
            />
          </label>
          <div className="mt-6 flex justify-end gap-2">
            <AlertDialog.Cancel asChild>
              <Button variant="outline">Назад</Button>
            </AlertDialog.Cancel>
            <AlertDialog.Action asChild>
              <Button className="bg-danger text-paper hover:bg-danger/90" onClick={() => onConfirm(reason)}>
                {confirmLabel}
              </Button>
            </AlertDialog.Action>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  )
}
