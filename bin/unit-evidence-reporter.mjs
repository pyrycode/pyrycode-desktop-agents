// Vitest's JSON reporter omits global unhandled errors. Keep those separately
// so a simultaneous named failure can never conceal an unfinished runner.
import { writeFileSync } from 'node:fs'

export default class UnitEvidenceReporter {
  onFinished(files = [], errors = []) {
    const suiteErrors = []
    const visit = task => {
      if (task.type === 'suite' && task.result?.errors?.length) {
        suiteErrors.push({ name: task.name, errors: task.result.errors.map(error => String(error.message ?? error)) })
      }
      for (const child of task.tasks ?? []) visit(child)
    }
    for (const file of files) visit(file)
    writeFileSync(process.env.PYRY_DESKTOP_UNIT_AUDIT_PATH, JSON.stringify({
      version: 1, completed: true, suiteErrors,
      unhandledErrors: errors.map(error => String(error.message ?? error))
    }))
  }
}
