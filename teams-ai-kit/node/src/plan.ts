/**
 * Plan parsing — the wire format between models and the AI executor.
 *
 * A model replies with one or more plan commands:
 *
 *   SAY <text>                     reply to the user (ends the turn)
 *   DO <action> <json-args>        invoke an action, then continue planning
 *
 * This is deliberately provider-agnostic: it works identically with OpenAI,
 * Azure OpenAI, and the MockModel, and it is trivial to prompt for.
 */

export type PlanCommand =
  | { type: "SAY"; text: string }
  | { type: "DO"; action: string; args: Record<string, any> };

export class PlanFormatError extends Error {}

export function parsePlan(raw: string): PlanCommand[] {
  const lines = raw.trim().split(/\r?\n/);
  const commands: PlanCommand[] = [];
  let sayLines: string[] | null = null;

  const flushSay = () => {
    if (sayLines && sayLines.length > 0) {
      commands.push({ type: "SAY", text: sayLines.join("\n").trim() });
    }
    sayLines = null;
  };

  for (const line of lines) {
    const say = /^SAY\s*(.*)$/i.exec(line);
    const doCmd = /^DO\s+([A-Za-z0-9_.-]+)\s*(.*)$/i.exec(line);
    if (say && !sayLines) {
      sayLines = [say[1]];
      continue;
    }
    if (doCmd) {
      flushSay();
      let args: Record<string, any> = {};
      const rest = doCmd[2].trim();
      if (rest) {
        try {
          const parsed = JSON.parse(rest);
          args = parsed && typeof parsed === "object" ? parsed : { value: parsed };
        } catch {
          throw new PlanFormatError(`DO command has invalid JSON arguments: ${rest.slice(0, 60)}`);
        }
      }
      commands.push({ type: "DO", action: doCmd[1], args });
      continue;
    }
    if (sayLines) sayLines.push(line); // continuation lines extend a SAY
  }
  flushSay();

  if (commands.length === 0) {
    // Tolerate models that answer plainly: treat the whole output as speech.
    const text = raw.trim();
    if (text) return [{ type: "SAY", text }];
    throw new PlanFormatError("The model returned an empty plan.");
  }
  return commands;
}
