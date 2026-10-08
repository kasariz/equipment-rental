import * as Dialog from '@radix-ui/react-dialog'
import { useState, type ReactNode } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { useCreateReview, type ReviewTarget } from '@/features/reviews/api'
import { StarPicker } from './Stars'

const COPY = {
  owner: {
    title: 'Отзыв о владельце',
    question: (name: string) => `Как прошла аренда у ${name}? Отзыв увидят другие арендаторы.`,
    placeholder: 'Пунктуальность, состояние техники, работа оператора',
  },
  renter: {
    title: 'Отзыв об арендаторе',
    question: (name: string) => `Каким клиентом был ${name}? Отзыв увидят другие владельцы техники.`,
    placeholder: 'Пунктуальность, оплата, условия на объекте',
  },
} as const

type Props = { bookingId: number; subjectName: string; target: ReviewTarget; trigger: ReactNode }

export function ReviewDialog({ bookingId, subjectName, target, trigger }: Props) {
  const copy = COPY[target]
  const [open, setOpen] = useState(false)
  const [rating, setRating] = useState(0)
  const [text, setText] = useState('')
  const create = useCreateReview()

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => {
        setOpen(o)
        if (o) {
          setRating(0)
          setText('')
        }
      }}
    >
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[2000] bg-ink/50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 z-[2001] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-paper p-6 shadow-xl">
          <Dialog.Title className="font-display text-lg font-semibold">{copy.title}</Dialog.Title>
          <Dialog.Description className="mt-1 text-steel">{copy.question(subjectName)}</Dialog.Description>
          <form
            className="mt-5 flex flex-col gap-4"
            onSubmit={(e) => {
              e.preventDefault()
              if (!rating) return
              create.mutate(
                { bookingId, rating, text, target },
                {
                  onSuccess: () => {
                    toast.success('Спасибо за отзыв')
                    setOpen(false)
                  },
                  onError: (err) => toast.error(err.message),
                },
              )
            }}
          >
            <StarPicker value={rating} onChange={setRating} />
            <label className="flex flex-col gap-1.5 text-sm font-medium">
              Комментарий (необязательно)
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                maxLength={2000}
                placeholder={copy.placeholder}
                className="min-h-24 rounded-md border border-line bg-paper px-3 py-2 text-[15px] font-normal focus-visible:border-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal"
              />
            </label>
            <div className="flex justify-end gap-2">
              <Dialog.Close asChild>
                <Button type="button" variant="outline">
                  Отмена
                </Button>
              </Dialog.Close>
              <Button type="submit" disabled={!rating || create.isPending}>
                {create.isPending ? 'Отправляем…' : 'Отправить'}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
