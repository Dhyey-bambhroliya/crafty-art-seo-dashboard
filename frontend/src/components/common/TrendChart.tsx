import React, { useState } from 'react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip,
  CartesianGrid, Legend
} from 'recharts';
import { DailyTrendPoint } from '../../types';

interface TrendChartProps {
  data: DailyTrendPoint[];
  title?: string;
  subtitle?: string;
}

export const TrendChart: React.FC<TrendChartProps> = ({
  data,
  title = "Traffic Performance Over Time",
  subtitle = "Daily comparison of current 28 days vs previous 28 days (aligned by day of week)"
}) => {
  const [metric, setMetric] = useState<'clicks' | 'impressions' | 'ctr' | 'position'>('clicks');

  const metricConfig = {
    clicks: {
      currentKey: 'current_clicks',
      previousKey: 'previous_clicks',
      label: 'Clicks',
      color: '#6366f1', // Indigo
      prevColor: '#94a3b8', // Slate
      formatter: (val: number) => val.toLocaleString(),
    },
    impressions: {
      currentKey: 'current_impressions',
      previousKey: 'previous_impressions',
      label: 'Impressions',
      color: '#8b5cf6', // Violet
      prevColor: '#64748b',
      formatter: (val: number) => val.toLocaleString(),
    },
    ctr: {
      currentKey: 'ctr',
      previousKey: undefined,
      label: 'CTR (%)',
      color: '#10b981', // Emerald
      prevColor: '#64748b',
      formatter: (val: number) => `${val}%`,
    },
    position: {
      currentKey: 'position',
      previousKey: undefined,
      label: 'Avg Position',
      color: '#f59e0b', // Amber
      prevColor: '#64748b',
      formatter: (val: number) => val.toFixed(1),
    },
  };

  const currentConf = metricConfig[metric];

  return (
    <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 shadow-xl shadow-black/20">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-lg font-bold text-white tracking-tight">{title}</h2>
          <p className="text-xs text-slate-400 mt-1">{subtitle}</p>
        </div>

        {/* Metric Switcher Tab Buttons */}
        <div className="flex items-center space-x-1 p-1 bg-slate-950/80 rounded-xl border border-slate-800 self-start">
          <button
            onClick={() => setMetric('clicks')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              metric === 'clicks'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Clicks
          </button>
          <button
            onClick={() => setMetric('impressions')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              metric === 'impressions'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Impressions
          </button>
          <button
            onClick={() => setMetric('ctr')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              metric === 'ctr'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            CTR
          </button>
          <button
            onClick={() => setMetric('position')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              metric === 'position'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Avg Position
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className="h-72 w-full">
        {data && data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="currentGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={currentConf.color} stopOpacity={0.35} />
                  <stop offset="95%" stopColor={currentConf.color} stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="prevGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={currentConf.prevColor} stopOpacity={0.15} />
                  <stop offset="95%" stopColor={currentConf.prevColor} stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey="date"
                stroke="#64748b"
                tick={{ fill: '#64748b', fontSize: 11 }}
                axisLine={{ stroke: '#334155' }}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: '#64748b', fontSize: 11 }}
                axisLine={{ stroke: '#334155' }}
                tickFormatter={currentConf.formatter}
                reversed={metric === 'position'} // Inverted Y-axis for position
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  border: '1px solid #334155',
                  borderRadius: '12px',
                  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
                  fontSize: '12px',
                  color: '#f8fafc',
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
                formatter={(val) => <span className="text-slate-300 font-medium">{val}</span>}
              />
              {currentConf.previousKey && (
                <Area
                  type="monotone"
                  dataKey={currentConf.previousKey}
                  name="Previous 28 Days"
                  stroke={currentConf.prevColor}
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  fillOpacity={1}
                  fill="url(#prevGradient)"
                />
              )}
              <Area
                type="monotone"
                dataKey={currentConf.currentKey}
                name="Current 28 Days"
                stroke={currentConf.color}
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#currentGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-slate-500 text-sm">
            No historical metric trend data available.
          </div>
        )}
      </div>
    </div>
  );
};
