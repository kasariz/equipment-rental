import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getErrorMessage } from '@/api/client'

export function useOwnerReviews(ownerId: number) {
  return useQuery({
    queryKey: ['reviews', 'owner', ownerId],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/owners/{owner_id}/reviews', {
        params: { path: { owner_id: ownerId } },
      })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
  })
}

export type ReviewTarget = 'owner' | 'renter'

export function useRenterReviews(renterId: number, enabled: boolean) {
  return useQuery({
    queryKey: ['reviews', 'renter', renterId],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/renters/{renter_id}/reviews', {
        params: { path: { renter_id: renterId } },
      })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    enabled,
  })
}

export function useMyRatings() {
  return useQuery({
    queryKey: ['reviews', 'my-ratings'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/my/ratings')
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
  })
}

export function useCreateReview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      bookingId,
      rating,
      text,
      target,
    }: {
      bookingId: number
      rating: number
      text: string
      target: ReviewTarget
    }) => {
      const options = { params: { path: { booking_id: bookingId } }, body: { rating, text: text.trim() || null } }
      const { data, error } =
        target === 'owner'
          ? await api.POST('/api/bookings/{booking_id}/review', options)
          : await api.POST('/api/bookings/{booking_id}/renter-review', options)
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bookings'] })
      qc.invalidateQueries({ queryKey: ['reviews'] })
      qc.invalidateQueries({ queryKey: ['equipment'] })
    },
  })
}
