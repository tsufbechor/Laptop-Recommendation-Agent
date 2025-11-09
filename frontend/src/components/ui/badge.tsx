import * as React from "react";

import { cn } from "../../utils/cn";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "outline" | "success";
}

const badgeClasses: Record<NonNullable<BadgeProps["variant"]>, string> = {
  default: "bg-secondary text-secondary-foreground",
  outline: "border border-slate-700 text-slate-200",
  success: "bg-accent/20 text-accent border border-accent/40"
};

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(({ className, variant = "default", ...props }, ref) => (
  <span
    ref={ref}
    className={cn(
      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide",
      badgeClasses[variant],
      className
    )}
    {...props}
  />
));

Badge.displayName = "Badge";

export { Badge };
