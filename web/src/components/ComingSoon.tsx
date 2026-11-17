import { EmptyState } from '@/components/StatusViews'

export function ComingSoon({ title, children }: { title: string; children: string }) {
  return (
    <section className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
      <EmptyState title="Em breve">{children}</EmptyState>
    </section>
  )
}
