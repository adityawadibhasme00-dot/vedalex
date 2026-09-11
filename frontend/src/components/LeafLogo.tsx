'use client';
import React from 'react';
import { Leaf } from 'lucide-react';

export default React.memo(function LeafLogo({ className = '' }: { className?: string }) {
  return (
    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center shadow-lg ${className}`}>
      <Leaf className="w-5 h-5 text-white" />
    </div>
  );
});
