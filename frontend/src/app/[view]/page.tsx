import { notFound } from 'next/navigation';
import { ClientApp } from '@/components/layout/ClientApp';
import type { View } from '@/store/useHealthStore';

const VIEW_IDS: View[] = [
  'dashboard',
  'analytics',
  'assistant',
  'training',
  'history',
  'crew',
  'radar',
  'routine',
  'learn',
  'data',
  'simulation',
];

/** Allows direct navigation to client-side views without treating them as unknown pages. */
export default function ViewRoute({ params }: { params: { view: string } }) {
  const view = params.view as View;
  if (!VIEW_IDS.includes(view)) notFound();
  return <ClientApp initialView={view} />;
}
