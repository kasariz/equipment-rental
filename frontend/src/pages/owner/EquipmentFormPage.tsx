import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient } from '@tanstack/react-query'
import { ImagePlus, Plus, Trash2, X } from 'lucide-react'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Controller, useFieldArray, useForm, useWatch } from 'react-hook-form'
import { Link, useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'
import { z } from 'zod'
import type { Equipment, EquipmentStatus, Photo } from '@/api/client'
import { LocationPicker } from '@/components/map/LocationPicker'
import { PageSpinner } from '@/components/PageSpinner'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { useCategories, useEquipment } from '@/features/catalog/api'
import {
  deletePhoto,
  uploadPhotos,
  useCreateEquipment,
  useUpdateEquipment,
  type EquipmentCreateBody,
} from '@/features/owner/api'
import { statusLabels } from '@/lib/format'
import { NotFoundPage } from '../NotFoundPage'

const MAX_PHOTOS = 10
const MONEY_RE = /^\d{1,8}([.,]\d{1,2})?$/
const toNumber = (v: string) => Number(v.replace(',', '.'))

const schema = z
  .object({
    name: z.string().trim().min(2, 'Введите название, например «JCB 3CX»').max(255),
    category_id: z.string().min(1, 'Выберите категорию'),
    description: z.string().max(5000),
    specs: z.array(z.object({ name: z.string().trim().max(100), value: z.string().trim().max(200) })).max(30),
    address: z.string().trim().max(255),
    location: z.object({ lat: z.number(), lng: z.number() }).nullable(),
    price_per_hour: z.string().trim().regex(MONEY_RE, 'Введите цену, например 2500'),
    price_per_shift: z.string().trim().refine((v) => v === '' || MONEY_RE.test(v), 'Введите цену, например 18000'),
    min_hours: z.string().regex(/^\d+$/, 'Целое число часов').refine((v) => +v >= 1 && +v <= 24, 'От 1 до 24 часов'),
    operator_available: z.boolean(),
    operator_price_per_hour: z.string().trim(),
    status: z.enum(['available', 'maintenance', 'inactive']),
  })
  .superRefine((v, ctx) => {
    if (!v.location) {
      ctx.addIssue({ code: 'custom', path: ['location'], message: 'Отметьте на карте, где стоит техника' })
    }
    if (toNumber(v.price_per_hour) <= 0) {
      ctx.addIssue({ code: 'custom', path: ['price_per_hour'], message: 'Цена должна быть больше нуля' })
    }
    if (v.operator_available && !MONEY_RE.test(v.operator_price_per_hour)) {
      ctx.addIssue({ code: 'custom', path: ['operator_price_per_hour'], message: 'Укажите цену оператора за час' })
    }
    v.specs.forEach((s, i) => {
      if (s.name && !s.value) ctx.addIssue({ code: 'custom', path: ['specs', i, 'value'], message: 'Укажите значение' })
      if (!s.name && s.value) ctx.addIssue({ code: 'custom', path: ['specs', i, 'name'], message: 'Укажите название' })
    })
  })
type FormValues = z.infer<typeof schema>

const emptyValues: FormValues = {
  name: '',
  category_id: '',
  description: '',
  specs: [{ name: '', value: '' }],
  address: '',
  location: null,
  price_per_hour: '',
  price_per_shift: '',
  min_hours: '4',
  operator_available: false,
  operator_price_per_hour: '',
  status: 'available',
}

function fromEquipment(e: Equipment): FormValues {
  return {
    name: e.name,
    category_id: String(e.category.id),
    description: e.description ?? '',
    specs: e.specs.length ? e.specs : [{ name: '', value: '' }],
    address: e.address ?? '',
    location: { lat: e.latitude, lng: e.longitude },
    price_per_hour: String(e.price_per_hour),
    price_per_shift: e.price_per_shift != null ? String(e.price_per_shift) : '',
    min_hours: String(e.min_hours),
    operator_available: e.operator_available,
    operator_price_per_hour: e.operator_price_per_hour != null ? String(e.operator_price_per_hour) : '',
    status: e.status,
  }
}

function toBody(v: FormValues): EquipmentCreateBody {
  return {
    name: v.name.trim(),
    category_id: Number(v.category_id),
    description: v.description.trim() || null,
    specs: v.specs.filter((s) => s.name && s.value),
    address: v.address.trim() || null,
    latitude: v.location!.lat,
    longitude: v.location!.lng,
    price_per_hour: toNumber(v.price_per_hour),
    price_per_shift: v.price_per_shift ? toNumber(v.price_per_shift) : null,
    min_hours: Number(v.min_hours),
    operator_available: v.operator_available,
    operator_price_per_hour: v.operator_price_per_hour ? toNumber(v.operator_price_per_hour) : null,
  }
}

const textareaClass =
  'min-h-28 w-full rounded-md border border-line bg-paper px-3.5 py-2.5 text-[15px] hover:border-steel focus-visible:border-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal'
const selectClass =
  'h-11 w-full rounded-md border border-line bg-paper px-3 text-[15px] hover:border-steel focus-visible:border-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal aria-invalid:border-danger'

function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="grid gap-5 border-t border-line pt-8 md:grid-cols-[220px_1fr] md:gap-10">
      <div>
        <h2 className="font-display text-lg font-semibold">{title}</h2>
        {hint && <p className="mt-1.5 text-sm text-steel">{hint}</p>}
      </div>
      <div className="flex flex-col gap-5">{children}</div>
    </section>
  )
}

/**
 * Фото в форме: уже сохранённые и новые вперемешку.
 * Ничего не уходит на сервер, пока не нажата кнопка сохранения — так же, как с текстовыми полями.
 */
function PhotosEditor({
  saved,
  newFiles,
  onRemoveSaved,
  onChangeNew,
}: {
  saved: Photo[]
  newFiles: File[]
  onRemoveSaved: (id: number) => void
  onChangeNew: (files: File[]) => void
}) {
  const previews = useMemo(() => newFiles.map((f) => URL.createObjectURL(f)), [newFiles])
  useEffect(() => () => previews.forEach((url) => URL.revokeObjectURL(url)), [previews])
  const free = MAX_PHOTOS - saved.length - newFiles.length

  return (
    <PhotoGrid
      photos={[
        ...saved.map((p) => ({ key: `saved-${p.id}`, url: p.url, onRemove: () => onRemoveSaved(p.id) })),
        ...previews.map((url, i) => ({
          key: url,
          url,
          isNew: true,
          onRemove: () => onChangeNew(newFiles.filter((_, j) => j !== i)),
        })),
      ]}
      canAdd={free > 0}
      onAdd={(added) => onChangeNew([...newFiles, ...added.slice(0, free)])}
    />
  )
}

function PhotoGrid({
  photos,
  canAdd,
  onAdd,
}: {
  photos: { key: string; url: string; isNew?: boolean; onRemove: () => void }[]
  canAdd: boolean
  onAdd: (files: File[]) => void
}) {
  return (
    <div>
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {photos.map((p, i) => (
          <li key={p.key} className="relative">
            <img src={p.url} alt={`Фото ${i + 1}`} className="aspect-[4/3] w-full rounded-md object-cover" />
            {(i === 0 || p.isNew) && (
              <span className="absolute bottom-2 left-2 rounded bg-ink/80 px-2 py-0.5 text-xs text-paper">
                {i === 0 ? 'Обложка' : 'Новое'}
              </span>
            )}
            <button
              type="button"
              onClick={p.onRemove}
              aria-label={`Удалить фото ${i + 1}`}
              className="absolute top-2 right-2 flex size-8 items-center justify-center rounded-full bg-paper/90 text-ink shadow hover:bg-paper"
            >
              <X className="size-4" />
            </button>
          </li>
        ))}
        {canAdd && (
          <li>
            <label
              className="flex aspect-[4/3] cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed border-line text-sm text-steel transition-colors hover:border-ink hover:text-ink has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ink"
            >
              <ImagePlus className="size-6" aria-hidden />
              Добавить фото
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                className="sr-only"
                onChange={(e) => {
                  const files = Array.from(e.target.files ?? [])
                  if (files.length) onAdd(files)
                  e.target.value = ''
                }}
              />
            </label>
          </li>
        )}
      </ul>
      <p className="mt-2 text-sm text-steel">До {MAX_PHOTOS} фото в JPG, PNG или WebP. Первое фото станет обложкой.</p>
    </div>
  )
}

function EquipmentForm({ item }: { item?: Equipment }) {
  const isEdit = Boolean(item)
  const navigate = useNavigate()
  const { data: categories } = useCategories()
  const create = useCreateEquipment()
  const update = useUpdateEquipment(item?.id ?? 0)
  const queryClient = useQueryClient()
  const [newFiles, setNewFiles] = useState<File[]>([])
  const [removedPhotoIds, setRemovedPhotoIds] = useState<number[]>([])
  const [savingPhotos, setSavingPhotos] = useState(false)

  const { register, control, handleSubmit, reset, formState: { errors, isDirty } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: item ? fromEquipment(item) : emptyValues,
  })
  const specs = useFieldArray({ control, name: 'specs' })
  const operatorAvailable = useWatch({ control, name: 'operator_available' })

  const savedPhotos = item?.photos.filter((p) => !removedPhotoIds.includes(p.id)) ?? []
  const photosChanged = newFiles.length > 0 || removedPhotoIds.length > 0

  const onSubmit = async (values: FormValues) => {
    const body = toBody(values)

    if (item) {
      try {
        if (isDirty) await update.mutateAsync({ ...body, status: values.status })
        if (photosChanged) {
          setSavingPhotos(true)
          // Сначала удаляем: иначе можно упереться в лимит 10 фото при замене снимков
          for (const id of removedPhotoIds) await deletePhoto(item.id, id)
          if (newFiles.length) await uploadPhotos(item.id, newFiles)
        }
        reset(values) // сохранённое становится новой точкой отсчёта для «есть изменения»
        setNewFiles([])
        setRemovedPhotoIds([])
        toast.success('Изменения сохранены')
      } catch (e) {
        toast.error((e as Error).message)
      } finally {
        setSavingPhotos(false)
        await queryClient.invalidateQueries({ queryKey: ['equipment'] })
      }
      return
    }

    try {
      const created = await create.mutateAsync(body)
      if (newFiles.length) {
        setSavingPhotos(true)
        try {
          await uploadPhotos(created.id, newFiles)
        } catch (e) {
          toast.error(`Техника сохранена, но фото не загрузились: ${(e as Error).message}`)
          navigate(`/my/equipment/${created.id}/edit`, { replace: true })
          return
        } finally {
          setSavingPhotos(false)
        }
        await queryClient.invalidateQueries({ queryKey: ['equipment'] })
      }
      toast.success('Техника добавлена')
      navigate('/my/equipment')
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  const saving = create.isPending || update.isPending || savingPhotos
  const err = (id: string, message?: string) => ({
    'aria-invalid': Boolean(message),
    'aria-describedby': message ? `${id}-error` : undefined,
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-8">
      <Section title="Основное">
        <Field id="name" label="Название" error={errors.name?.message} hint="Марка и модель, как в ПТС">
          <Input id="name" placeholder="JCB 3CX Super" {...err('name', errors.name?.message)} {...register('name')} />
        </Field>
        <Field id="category_id" label="Категория" error={errors.category_id?.message}>
          <select id="category_id" className={selectClass} {...err('category_id', errors.category_id?.message)} {...register('category_id')}>
            <option value="">Выберите категорию</option>
            {categories?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </Field>
        {isEdit && (
          <Field id="status" label="Статус" hint="Техника на ремонте или снятая с размещения не видна в каталоге">
            <select id="status" className={selectClass} {...register('status')}>
              {(Object.keys(statusLabels) as EquipmentStatus[]).map((s) => (
                <option key={s} value={s}>
                  {statusLabels[s]}
                </option>
              ))}
            </select>
          </Field>
        )}
        <Field id="description" label="Описание (необязательно)" error={errors.description?.message}>
          <textarea
            id="description"
            className={textareaClass}
            placeholder="Состояние, навесное оборудование, условия доставки"
            {...register('description')}
          />
        </Field>
      </Section>

      <Section title="Фото" hint="С фото объявление выглядит надёжнее">
        <PhotosEditor
          saved={savedPhotos}
          newFiles={newFiles}
          onRemoveSaved={(id) => setRemovedPhotoIds((ids) => [...ids, id])}
          onChangeNew={setNewFiles}
        />
      </Section>

      <Section title="Цены">
        <div className="grid gap-5 sm:grid-cols-2">
          <Field id="price_per_hour" label="За час, ₽" error={errors.price_per_hour?.message}>
            <Input id="price_per_hour" inputMode="decimal" placeholder="2500" {...err('price_per_hour', errors.price_per_hour?.message)} {...register('price_per_hour')} />
          </Field>
          <Field id="price_per_shift" label="За смену 8 часов, ₽" hint="Необязательно" error={errors.price_per_shift?.message}>
            <Input id="price_per_shift" inputMode="decimal" placeholder="18000" {...err('price_per_shift', errors.price_per_shift?.message)} {...register('price_per_shift')} />
          </Field>
          <Field id="min_hours" label="Минимальный заказ, часов" error={errors.min_hours?.message}>
            <Input id="min_hours" inputMode="numeric" {...err('min_hours', errors.min_hours?.message)} {...register('min_hours')} />
          </Field>
        </div>
        <label className="flex items-center gap-2.5 text-[15px]">
          <input type="checkbox" className="size-4 accent-ink" {...register('operator_available')} />
          Могу предоставить оператора
        </label>
        {operatorAvailable && (
          <div className="sm:w-1/2 sm:pr-2.5">
            <Field id="operator_price_per_hour" label="Оператор за час, ₽" error={errors.operator_price_per_hour?.message}>
              <Input
                id="operator_price_per_hour"
                inputMode="decimal"
                placeholder="600"
                {...err('operator_price_per_hour', errors.operator_price_per_hour?.message)}
                {...register('operator_price_per_hour')}
              />
            </Field>
          </div>
        )}
      </Section>

      <Section title="Где стоит техника" hint="Кликните по карте, чтобы поставить метку. Её можно перетащить">
        <Controller
          control={control}
          name="location"
          render={({ field, fieldState }) => (
            <div className="flex flex-col gap-1.5">
              <LocationPicker value={field.value} onChange={field.onChange} invalid={Boolean(fieldState.error)} />
              {fieldState.error && (
                <p role="alert" className="text-sm text-danger">
                  {fieldState.error.message}
                </p>
              )}
            </div>
          )}
        />
        <Field id="address" label="Адрес для арендаторов (необязательно)" hint="Район или улица, без номера дома">
          <Input id="address" placeholder="Ростов-на-Дону, Западный жилмассив" {...register('address')} />
        </Field>
      </Section>

      <Section title="Характеристики" hint="То, по чему выбирают технику: глубина копания, грузоподъёмность, масса">
        <ul className="flex flex-col gap-3">
          {specs.fields.map((f, i) => (
            <li key={f.id} className="grid grid-cols-[1fr_1fr_auto] items-start gap-2">
              <div>
                <Input
                  placeholder="Глубина копания"
                  aria-label={`Характеристика ${i + 1}: название`}
                  aria-invalid={Boolean(errors.specs?.[i]?.name)}
                  {...register(`specs.${i}.name`)}
                />
                {errors.specs?.[i]?.name && <p className="mt-1 text-sm text-danger">{errors.specs[i]?.name?.message}</p>}
              </div>
              <div>
                <Input
                  placeholder="5,9 м"
                  aria-label={`Характеристика ${i + 1}: значение`}
                  aria-invalid={Boolean(errors.specs?.[i]?.value)}
                  {...register(`specs.${i}.value`)}
                />
                {errors.specs?.[i]?.value && <p className="mt-1 text-sm text-danger">{errors.specs[i]?.value?.message}</p>}
              </div>
              <Button type="button" variant="ghost" className="size-11 px-0" aria-label={`Удалить характеристику ${i + 1}`} onClick={() => specs.remove(i)}>
                <Trash2 />
              </Button>
            </li>
          ))}
        </ul>
        {specs.fields.length < 30 && (
          <Button type="button" variant="outline" size="sm" className="self-start" onClick={() => specs.append({ name: '', value: '' })}>
            <Plus />
            Добавить характеристику
          </Button>
        )}
      </Section>

      <div className="sticky bottom-0 z-[1001] -mx-4 flex flex-wrap items-center gap-3 border-t border-line bg-concrete/95 px-4 py-4 backdrop-blur sm:-mx-6 sm:px-6">
        <Button type="submit" size="lg" disabled={saving || (isEdit && !isDirty && !photosChanged)}>
          {saving ? 'Сохраняем…' : isEdit ? 'Сохранить изменения' : 'Добавить технику'}
        </Button>
        <Button asChild variant="ghost" size="lg">
          <Link to="/my/equipment">Отмена</Link>
        </Button>
        {Object.keys(errors).length > 0 && (
          <p className="text-sm text-danger" role="alert">
            Проверьте поля, отмеченные красным
          </p>
        )}
      </div>
    </form>
  )
}

export function EquipmentCreatePage() {
  return (
    <div className="mx-auto max-w-5xl px-4 pt-10 sm:px-6 sm:pt-14">
      <h1 className="font-display mb-8 text-3xl font-semibold tracking-tight">Новая техника</h1>
      <EquipmentForm />
    </div>
  )
}

export function EquipmentEditPage() {
  const id = Number(useParams().id)
  const { data: item, isPending } = useEquipment(id)
  if (isPending) return <PageSpinner />
  if (!item) return <NotFoundPage />
  return (
    <div className="mx-auto max-w-5xl px-4 pt-10 sm:px-6 sm:pt-14">
      <h1 className="font-display mb-8 text-3xl font-semibold tracking-tight">{item.name}</h1>
      <EquipmentForm key={item.id} item={item} />
    </div>
  )
}
