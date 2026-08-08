interface PlaceholderSectionProps {
  title: string;
  story: string;
}

/** Placeholder para seções cujas stories ainda não foram implementadas */
export function PlaceholderSection({ title, story }: PlaceholderSectionProps) {
  return (
    <div className="flex h-full min-h-[200px] flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-border text-center text-muted-foreground">
      <p className="text-sm font-medium">{title}</p>
      <p className="text-xs">Em construção — {story}</p>
    </div>
  );
}
