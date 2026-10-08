import { Link } from 'react-router'
import { Button } from '@/components/ui/button'
import { useMe } from '@/features/auth/api'
import { useCategories } from '@/features/catalog/api'


export function HomePage() {
  const { data: categories } = useCategories()
  const { data: user } = useMe()
  // Владельцу — сразу в его технику, гостю — регистрация владельца.
  // Арендатору кнопка не показывается: сдавать технику с его аккаунта нельзя
  const isOwner = user?.role === 'owner' || user?.role === 'admin'
  const rentOutLink = isOwner ? '/my/equipment' : user ? null : '/register?role=owner'
  return (
    <>
      <section className="mx-auto max-w-6xl px-5 pt-14 pb-16 sm:px-6 sm:pt-24 sm:pb-24">
        <h1 className="font-display max-w-4xl text-4xl leading-[1.08] font-bold tracking-tight text-balance sm:text-6xl">
          Спецтехника на ваш объект на час, смену или неделю
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-steel">
          Экскаваторы, краны, погрузчики и самосвалы от владельцев поблизости. Выберите технику на карте,
          укажите время и адрес. Техника приезжает с оператором.
        </p>
        <div className="mt-10 flex flex-wrap gap-3">
          <Button asChild size="lg">
            <Link to="/catalog">Найти технику</Link>
          </Button>
          {rentOutLink && (
            <Button asChild size="lg" variant="outline">
              <Link to={rentOutLink}>{isOwner ? 'Моя техника' : 'Сдать свою технику'}</Link>
            </Button>
          )}
        </div>
      </section>

      <section className="border-t border-line bg-paper">
        <div className="mx-auto max-w-6xl px-5 py-12 sm:px-6">
          <h2 className="font-display text-xl font-semibold">Что можно арендовать</h2>
          <ul className="mt-6 flex flex-wrap gap-2.5">
            {categories?.map(({ slug, name }) => (
              <li key={slug}>
                <Link
                  to={`/catalog?category=${slug}`}
                  className="inline-block rounded-full border border-line px-4 py-2 text-[15px] transition-colors hover:border-ink hover:bg-signal/20"
                >
                  {name}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </>
  )
}
