'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { BloodworkCardData, Biomarker } from '../types';

interface BloodworkCardProps {
  data: BloodworkCardData;
}

function StatusIndicator({ status }: { status: Biomarker['status'] }) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium',
        status === 'normal' && 'bg-success/10 text-success',
        status === 'high' && 'bg-error/10 text-error',
        status === 'low' && 'bg-warning/10 text-warning',
      )}
    >
      {status === 'normal' ? 'Normal' : status === 'high' ? 'High' : 'Low'}
    </span>
  );
}

export default function BloodworkCard({ data }: BloodworkCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={cn(
        'rounded-[14px] border-[0.5px] border-border-default bg-canvas-elevated',
        'shadow-[0_1px_3px_rgba(42,36,51,0.04)] overflow-hidden',
      )}
    >
      <div className="px-4 py-3 border-b border-border-default flex items-center justify-between">
        <p className="text-sm font-semibold text-text-primary">
          Bloodwork Results
        </p>
        <p className="text-xs text-text-tertiary">{data.date}</p>
      </div>

      <div className="px-4 py-3 flex flex-col gap-3">
        {data.biomarkers.map((marker, i) => (
          <motion.div
            key={marker.id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2, delay: i * 0.08 }}
            className="flex items-center justify-between"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary truncate">
                {marker.name}
              </p>
              <p className="text-xs text-text-tertiary">
                Ref: {marker.referenceRange}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0 ml-3">
              <span className="text-sm font-medium text-text-primary">
                {marker.value} {marker.unit}
              </span>
              <StatusIndicator status={marker.status} />
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
