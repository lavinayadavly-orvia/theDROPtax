import * as React from "react"
import * as SliderPrimitive from "@radix-ui/react-slider"

import { cn } from "@/lib/utils"

const Slider = React.forwardRef(({ className, tooltipContent, tooltipColorClass, ...props }, ref) => (
  <SliderPrimitive.Root
    ref={ref}
    className={cn("relative flex w-full touch-none select-none items-center", className)}
    {...props}>
    <SliderPrimitive.Track
      className="relative h-1.5 w-full grow overflow-hidden rounded-full bg-primary/20">
      <SliderPrimitive.Range className="absolute h-full bg-primary" />
    </SliderPrimitive.Track>
    <SliderPrimitive.Thumb
      className="block h-4 w-4 rounded-full border border-primary/50 bg-background shadow transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 relative group"
    >
      {tooltipContent && (
        <div
          className={cn(
            "absolute bottom-6 left-1/2 -translate-x-1/2 px-3 py-2 bg-[#121212] font-medium text-[10px] rounded-md shadow-2xl border z-[100] pointer-events-none opacity-0 group-hover:opacity-100 focus-within:opacity-100 data-[state=dragging]:opacity-100 transition-opacity flex flex-col items-center min-w-[200px] text-center",
            tooltipColorClass || "text-white border-white/20"
          )}
        >
          {tooltipContent}
          <div className="absolute -bottom-[5px] left-1/2 -translate-x-1/2 w-2 h-2 bg-[#121212] rotate-45 border-r border-b" style={{ borderColor: 'inherit' }}></div>
        </div>
      )}
    </SliderPrimitive.Thumb>
  </SliderPrimitive.Root>
))
Slider.displayName = SliderPrimitive.Root.displayName

export { Slider }
