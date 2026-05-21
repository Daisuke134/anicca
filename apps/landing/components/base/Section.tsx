import React from 'react'
import Container from './Container'
import { cn } from '@/lib/utils'

type Props = React.PropsWithChildren<{
  id?: string
  className?: string
  muted?: boolean
}>

export default function Section({ id, children, className = '', muted = false }: Props) {
  return (
    <section id={id} className={cn('py-20', muted ? 'bg-muted' : 'bg-background', className)}>
      <Container>
        {children}
      </Container>
    </section>
  )
}


