/**
 * Localization — per-locale string dictionaries with a fallback chain.
 * The active locale comes from activity.locale (Teams sends e.g. "en-US"),
 * falling back to the language part, then to the default locale.
 */

export class Localization {
  private dictionaries = new Map<string, Record<string, string>>();
  private fallback: string;

  constructor(defaultLocale = "en") {
    this.fallback = defaultLocale;
  }

  add(locale: string, dictionary: Record<string, string>): this {
    this.dictionaries.set(locale.toLowerCase(), dictionary);
    return this;
  }

  resolveLocale(locale?: string): string {
    const wanted = (locale ?? this.fallback).toLowerCase();
    if (this.dictionaries.has(wanted)) return wanted;
    const language = wanted.split("-")[0];
    if (this.dictionaries.has(language)) return language;
    return this.fallback;
  }

  t(locale: string | undefined, key: string, vars: Record<string, string> = {}): string {
    const dict = this.dictionaries.get(this.resolveLocale(locale)) ?? {};
    let text = dict[key] ?? this.dictionaries.get(this.fallback)?.[key] ?? key;
    for (const [name, value] of Object.entries(vars)) {
      text = text.replaceAll(`{{${name}}}`, value);
    }
    return text;
  }
}
