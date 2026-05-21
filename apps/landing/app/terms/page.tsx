'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function TermsIndex() {
  const router = useRouter()

  useEffect(() => {
    const lang = navigator.language.startsWith('ja') ? 'ja' : 'en'
    router.replace(`/terms/${lang}`)
  }, [router])

  return null
}
