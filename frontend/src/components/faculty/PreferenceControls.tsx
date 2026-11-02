/** Native controls retain keyboard, form and disabled-fieldset behavior. */
export function PreferenceSwitch({label, checked, onChange}: {label: string; checked: boolean; onChange: (checked: boolean) => void}) {
  return <label className="preference-switch">
    <span className="preference-switch-control">
      <input className="preference-switch-input" type="checkbox" role="switch" aria-label={label} checked={checked} onChange={event => onChange(event.target.checked)}/>
      <span className="preference-switch-track" aria-hidden="true"><span className="preference-switch-thumb"/></span>
    </span>
    <span className="preference-switch-label">{label}</span>
    <span className="preference-switch-state" aria-hidden="true">{checked ? "ON" : "OFF"}</span>
  </label>;
}

export function PreferenceChoices<T extends string>({label, name, value, options, onChange}: {
  label: string; name: string; value: T; options: readonly {value: T; label: string}[]; onChange: (value: T) => void;
}) {
  return <fieldset className="preference-segmented"><legend className="sr-only">{label}</legend>
    <div className="preference-segments">{options.map(option => <label key={option.value} className="preference-segment">
      <input className="preference-radio" type="radio" name={name} value={option.value} checked={value === option.value} onChange={() => onChange(option.value)}/>
      <span className="preference-segment-label">{option.label}</span>
    </label>)}</div>
  </fieldset>;
}
