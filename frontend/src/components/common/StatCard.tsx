import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface StatCardProps {
  title: string;
  currentValue: string | number;
  previousValue?: string | number;
  diff?: number;
  pctChange?: number;
  isPosition?: boolean;
  prefix?: string;
  suffix?: string;
  subtext?: string;
  icon?: React.ReactNode;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  currentValue,
  previousValue,
  diff,
  pctChange,
  isPosition = false,
  prefix = '',
  suffix = '',
  subtext,
  icon,
}) => {
  // For position, a negative diff means improved ranking (e.g. 5.0 -> 3.0 is -2.0 -> good!)
  const isPositive = isPosition
    ? (diff !== undefined && diff < -0.2)
    : (diff !== undefined && diff > 0);

  const isNeutral = diff === undefined || Math.abs(diff) <= (isPosition ? 0.2 : 0);

  return (
    <div className="bg-slate-900/90 rounded-2xl p-5 border border-slate-800/80 shadow-lg shadow-black/20 hover:border-slate-700/80 transition-all flex flex-col justify-between">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{title}</span>
        {icon && <div className="text-slate-400 p-2 rounded-xl bg-slate-800/60 border border-slate-700/40">{icon}</div>}
      </div>

      <div className="my-3">
        <div className="text-2xl font-bold text-white tracking-tight">
          {prefix}{typeof currentValue === 'number' ? currentValue.toLocaleString() : currentValue}{suffix}
        </div>

        {previousValue !== undefined && (
          <div className="text-xs text-slate-400 mt-0.5">
            Prev 28d: <span className="text-slate-300 font-medium">{prefix}{typeof previousValue === 'number' ? previousValue.toLocaleString() : previousValue}{suffix}</span>
          </div>
        )}
      </div>

      <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-xs">
        {diff !== undefined ? (
          <div className="flex items-center space-x-1.5">
            <span
              className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full font-semibold text-[11px] ${
                isNeutral
                  ? 'bg-slate-800 text-slate-300'
                  : isPositive
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                  : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
              }`}
            >
              {isNeutral ? (
                <Minus className="w-3 h-3" />
              ) : isPositive ? (
                <TrendingUp className="w-3 h-3" />
              ) : (
                <TrendingDown className="w-3 h-3" />
              )}
              <span>
                {pctChange !== undefined ? `${pctChange > 0 ? '+' : ''}${pctChange}%` : `${diff > 0 ? '+' : ''}${diff}`}
              </span>
            </span>
            <span className="text-slate-400 text-[11px]">vs prev 28d</span>
          </div>
        ) : (
          <span className="text-slate-400 text-[11px]">{subtext || 'Active records'}</span>
        )}
      </div>
    </div>
  );
};
