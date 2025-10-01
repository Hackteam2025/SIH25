import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Area, AreaChart } from 'recharts';
import { FloatingCard } from '../ocean/FloatingCard';
import { OceanButton } from '../design-system/Button';
import { Activity, TrendingUp, Waves, Thermometer } from 'lucide-react';

interface DataPoint {
  depth: number;
  temperature: number;
  salinity: number;
  pressure: number;
  date: string;
}

interface OceanDataVizProps {
  data?: DataPoint[];
  title?: string;
  type?: 'profile' | 'timeseries' | 'scatter';
}

export const OceanDataViz: React.FC<OceanDataVizProps> = ({
  data = [],
  title = "Ocean Data Visualization",
  type = 'profile'
}) => {
  const [activeMetric, setActiveMetric] = useState<'temperature' | 'salinity' | 'pressure'>('temperature');
  const [animationKey, setAnimationKey] = useState(0);

  // Sample data for demo
  const sampleData: DataPoint[] = [
    { depth: 0, temperature: 25.2, salinity: 35.1, pressure: 0, date: '2024-01-01' },
    { depth: 50, temperature: 24.8, salinity: 35.2, pressure: 5, date: '2024-01-01' },
    { depth: 100, temperature: 22.1, salinity: 35.5, pressure: 10, date: '2024-01-01' },
    { depth: 200, temperature: 18.5, salinity: 35.8, pressure: 20, date: '2024-01-01' },
    { depth: 500, temperature: 12.3, salinity: 34.9, pressure: 50, date: '2024-01-01' },
    { depth: 1000, temperature: 6.2, salinity: 34.7, pressure: 100, date: '2024-01-01' },
    { depth: 1500, temperature: 3.1, salinity: 34.6, pressure: 150, date: '2024-01-01' },
    { depth: 2000, temperature: 1.8, salinity: 34.5, pressure: 200, date: '2024-01-01' }
  ];

  const displayData = data.length > 0 ? data : sampleData;

  const metrics = {
    temperature: {
      icon: Thermometer,
      color: '#FF6B6B',
      unit: '°C',
      label: 'Temperature'
    },
    salinity: {
      icon: Waves,
      color: '#4ECDC4',
      unit: 'PSU',
      label: 'Salinity'
    },
    pressure: {
      icon: Activity,
      color: '#0074D9',
      unit: 'dbar',
      label: 'Pressure'
    }
  };

  useEffect(() => {
    setAnimationKey(prev => prev + 1);
  }, [activeMetric]);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <FloatingCard className="p-3 min-w-[200px]" intensity="strong">
          <p className="ocean-heading text-sm mb-2">Depth: {label}m</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {entry.value.toFixed(2)} {metrics[activeMetric].unit}
            </p>
          ))}
        </FloatingCard>
      );
    }
    return null;
  };

  const renderChart = () => {
    const currentMetric = metrics[activeMetric];

    switch (type) {
      case 'profile':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart
              data={displayData}
              margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            >
              <defs>
                <linearGradient id={`colorGradient-${animationKey}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={currentMetric.color} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={currentMetric.color} stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis
                dataKey="depth"
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#003D7A', fontSize: 12 }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#003D7A', fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey={activeMetric}
                stroke={currentMetric.color}
                strokeWidth={3}
                fillOpacity={1}
                fill={`url(#colorGradient-${animationKey})`}
                animationDuration={1000}
              />
            </AreaChart>
          </ResponsiveContainer>
        );

      case 'timeseries':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart
              data={displayData}
              margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#003D7A', fontSize: 12 }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#003D7A', fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey={activeMetric}
                stroke={currentMetric.color}
                strokeWidth={3}
                dot={{ fill: currentMetric.color, strokeWidth: 2, r: 6 }}
                activeDot={{ r: 8, stroke: currentMetric.color }}
                animationDuration={1000}
              />
            </LineChart>
          </ResponsiveContainer>
        );

      default:
        return (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart
              data={displayData}
              margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis
                dataKey="depth"
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#003D7A', fontSize: 12 }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#003D7A', fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar
                dataKey={activeMetric}
                fill={currentMetric.color}
                radius={[4, 4, 0, 0]}
                animationDuration={1000}
              />
            </BarChart>
          </ResponsiveContainer>
        );
    }
  };

  return (
    <FloatingCard className="w-full">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="ocean-heading text-xl font-bold">{title}</h3>
          <p className="text-sm text-ocean-blue/70 mt-1">
            {displayData.length} data points • ARGO Float Data
          </p>
        </div>

        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-seafoam-green" />
          <span className="text-sm text-ocean-blue">Live Data</span>
        </div>
      </div>

      {/* Metric Selector */}
      <div className="flex gap-2 mb-6">
        {Object.entries(metrics).map(([key, metric]) => {
          const IconComponent = metric.icon;
          const isActive = activeMetric === key;

          return (
            <motion.button
              key={key}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setActiveMetric(key as typeof activeMetric)}
              className={`flex items-center gap-2 px-4 py-2 rounded-wave transition-all duration-300 ${
                isActive
                  ? 'bg-white/20 border border-white/30'
                  : 'glass-surface hover:bg-white/10'
              }`}
            >
              <IconComponent
                className="w-4 h-4"
                style={{ color: isActive ? metric.color : '#003D7A' }}
              />
              <span className={`text-sm font-medium ${
                isActive ? 'text-ocean-blue' : 'text-ocean-blue/70'
              }`}>
                {metric.label}
              </span>
            </motion.button>
          );
        })}
      </div>

      {/* Chart */}
      <div className="relative">
        {renderChart()}

        {/* Chart overlay for styling */}
        <div className="absolute inset-0 pointer-events-none bg-gradient-to-t from-white/5 to-transparent rounded-wave" />
      </div>

      {/* Stats Footer */}
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/10">
        <div className="flex items-center gap-4">
          <div className="text-center">
            <p className="text-xs text-ocean-blue/70">Min Depth</p>
            <p className="font-semibold text-ocean-blue">
              {Math.min(...displayData.map(d => d.depth))}m
            </p>
          </div>

          <div className="text-center">
            <p className="text-xs text-ocean-blue/70">Max Depth</p>
            <p className="font-semibold text-ocean-blue">
              {Math.max(...displayData.map(d => d.depth))}m
            </p>
          </div>

          <div className="text-center">
            <p className="text-xs text-ocean-blue/70">Avg {metrics[activeMetric].label}</p>
            <p className="font-semibold text-ocean-blue">
              {(displayData.reduce((acc, d) => acc + d[activeMetric], 0) / displayData.length).toFixed(2)} {metrics[activeMetric].unit}
            </p>
          </div>
        </div>

        <OceanButton size="sm" variant="secondary">
          Export Data
        </OceanButton>
      </div>
    </FloatingCard>
  );
};