
"use client";
import React from 'react';

interface GlassContainerProps {
    children: React.ReactNode;
    className?: string;
}

export const GlassContainer: React.FC<GlassContainerProps> = ({ children, className = "" }) => {
    return (
        <div className={`relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 shadow-2xl backdrop-blur-xl ${className}`}>
            {/* Glossy Overlay (Gradient) */}
            <div className="absolute inset-x-0 top-0 h-px w-full bg-gradient-to-r from-transparent via-white/30 to-transparent" />
            <div className="absolute inset-y-0 left-0 w-px h-full bg-gradient-to-b from-transparent via-white/10 to-transparent" />

            <div className="relative z-10 p-6">
                {children}
            </div>
        </div>
    );
};
