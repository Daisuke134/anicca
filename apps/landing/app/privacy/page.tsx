'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function PrivacyIndex() {
  const router = useRouter()
  
  useEffect(() => {
    const lang = navigator.language.startsWith('ja') ? 'ja' : 'en'
    router.replace(`/privacy/${lang}`)
  }, [router])
  
  return null
}
