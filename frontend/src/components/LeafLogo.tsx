'use client';
import React from 'react';
import { Leaf } from 'lucide-react';

export default React.memo(function LeafLogo({ className = '' }: { className?: string }) {
  return (
    <div className={`w-10 h-10 rounded-lg bg-gov-blue flex items-center justify-center ${className}`}>
      <Leaf className="w-5 h-5 text-white" />
    </div>
  );
});
