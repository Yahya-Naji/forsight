import * as React from "react";
import { cn } from "@/lib/utils";

// Wrapped in its own scroll container: the console renders wide registers and
// the page body must never scroll sideways.
const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>(
  ({ className, ...props }, ref) => (
    <div className="w-full overflow-x-auto">
      <table ref={ref} className={cn("w-full border-collapse text-sm", className)} {...props} />
    </div>
  ));
Table.displayName = "Table";

const TableHeader = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => <thead ref={ref} className={cn(className)} {...props} />);
TableHeader.displayName = "TableHeader";

const TableBody = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => <tbody ref={ref} className={cn(className)} {...props} />);
TableBody.displayName = "TableBody";

const TableRow = React.forwardRef<HTMLTableRowElement, React.HTMLAttributes<HTMLTableRowElement>>(
  ({ className, ...props }, ref) => (
    <tr ref={ref} className={cn("border-t border-line-soft", className)} {...props} />
  ));
TableRow.displayName = "TableRow";

/** Uppercase mono labels, matching the exported reports. */
const TableHead = React.forwardRef<HTMLTableCellElement, React.ThHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <th ref={ref} className={cn(
      "pb-2 pr-3 text-left font-mono text-[9.5px] font-semibold uppercase tracking-[1px] text-faint",
      className)} {...props} />
  ));
TableHead.displayName = "TableHead";

const TableCell = React.forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <td ref={ref} className={cn("py-2 pr-3 align-top", className)} {...props} />
  ));
TableCell.displayName = "TableCell";

/** Digits in a column must line up; this is used for every count. */
const TableNum = React.forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <td ref={ref} className={cn("py-2 pr-3 text-right align-top font-mono tabular-nums", className)} {...props} />
  ));
TableNum.displayName = "TableNum";

export { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableNum };
