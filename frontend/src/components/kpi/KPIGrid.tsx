import { cn } from '@/lib/utils';
import { KPICard, KPICardProps } from './KPICard';

export interface KPIGridProps {
  items: KPICardProps[];
  columns?: 2 | 3 | 4 | 5 | 6;
  className?: string;
}

const columnStyles = {
  2: 'grid-cols-1 sm:grid-cols-2',
  3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
  4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
  5: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5',
  6: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6',
};

export function KPIGrid({ items, columns = 4, className }: KPIGridProps) {
  return (
    <div className={cn('grid gap-4', columnStyles[columns], className)}>
      {items.map((item, index) => (
        <KPICard key={`kpi-${index}-${item.title}`} {...item} />
      ))}
    </div>
  );
}

export default KPIGrid;
