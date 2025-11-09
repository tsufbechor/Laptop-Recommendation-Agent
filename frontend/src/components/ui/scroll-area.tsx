import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area";

import { cn } from "../../utils/cn";

export const ScrollArea = ({ className, children }: { className?: string; children: React.ReactNode }) => (
  <ScrollAreaPrimitive.Root className={cn("relative overflow-hidden", className)}>
    <ScrollAreaPrimitive.Viewport className="h-full w-full rounded-[inherit]">{children}</ScrollAreaPrimitive.Viewport>
    <ScrollAreaPrimitive.Scrollbar
      orientation="vertical"
      className="flex w-2 touch-none select-none border-l border-l-transparent bg-slate-900/40 transition-colors"
    >
      <ScrollAreaPrimitive.Thumb className="relative flex-1 rounded-full bg-slate-700" />
    </ScrollAreaPrimitive.Scrollbar>
  </ScrollAreaPrimitive.Root>
);
