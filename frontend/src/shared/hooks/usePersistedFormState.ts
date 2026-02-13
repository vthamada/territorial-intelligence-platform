import { useCallback, useState } from "react";

type FormValues = Record<string, string>;

const STORAGE_PREFIX = "tip_form_";

function loadFromStorage(key: string): FormValues | null {
  try {
    const raw = localStorage.getItem(`${STORAGE_PREFIX}${key}`);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as unknown;
    if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)) {
      return parsed as FormValues;
    }
    return null;
  } catch {
    return null;
  }
}

function saveToStorage(key: string, values: FormValues) {
  try {
    localStorage.setItem(`${STORAGE_PREFIX}${key}`, JSON.stringify(values));
  } catch {
    // storage full or unavailable — ignore
  }
}

function clearStorage(key: string) {
  try {
    localStorage.removeItem(`${STORAGE_PREFIX}${key}`);
  } catch {
    // ignore
  }
}

/**
 * Hook to persist form field values in localStorage.
 *
 * Priority: query string params > localStorage > defaults.
 *
 * @param storageKey - Unique key for this form (e.g., "scenarios", "briefs")
 * @param defaults  - Default field values
 * @param queryOverrides - Values from URL search params (take precedence)
 * @returns [values, setField, clearPersisted]
 */
export function usePersistedFormState(
  storageKey: string,
  defaults: FormValues,
  queryOverrides: FormValues = {}
): [FormValues, (field: string, value: string) => void, () => void] {
  const [values, setValues] = useState<FormValues>(() => {
    const saved = loadFromStorage(storageKey);
    const initial = { ...defaults };

    // Merge saved values on top of defaults
    if (saved) {
      for (const [k, v] of Object.entries(saved)) {
        if (k in initial) {
          initial[k] = v;
        }
      }
    }

    // Query string params override everything
    for (const [k, v] of Object.entries(queryOverrides)) {
      if (v && k in initial) {
        initial[k] = v;
      }
    }

    return initial;
  });

  const setField = useCallback(
    (field: string, value: string) => {
      setValues((prev) => {
        const next = { ...prev, [field]: value };
        saveToStorage(storageKey, next);
        return next;
      });
    },
    [storageKey]
  );

  const clearPersisted = useCallback(() => {
    clearStorage(storageKey);
  }, [storageKey]);

  return [values, setField, clearPersisted];
}
