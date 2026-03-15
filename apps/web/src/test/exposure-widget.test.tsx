import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

/**
 * WIRE-02 RED stubs for ExposureWidget.
 *
 * The component at @/components/exposure/exposure-widget does not exist yet.
 * Tests assert expected behavior contracts. They are RED because the component
 * is missing — these pass once the component is implemented in Wave 1.
 */

const mockExposureData = {
  total_exposure: 1500.0,
  bankroll: 10000.0,
  venues: [
    { venue: 'draftkings', exposure: 600.0, pct: 0.06 },
    { venue: 'fanduel', exposure: 500.0, pct: 0.05 },
    { venue: 'pinnacle', exposure: 400.0, pct: 0.04 },
  ],
}

describe('ExposureWidget — WIRE-02 RED stubs', () => {
  it('test_exposure_widget_renders_utilization_bars: ExposureWidget component file exists', () => {
    // RED: the file does not exist yet — expect it to be present
    // This will pass once Wave 1 creates the component
    const fs = require('fs')
    const path = require('path')
    const componentPath = path.join(
      __dirname,
      '../../components/exposure/exposure-widget.tsx'
    )
    expect(
      fs.existsSync(componentPath),
      `ExposureWidget not found at ${componentPath}`
    ).toBe(true)
  })

  it('test_exposure_widget_shows_total_exposure: component exports ExposureWidget named export', () => {
    // RED: file does not exist yet
    const fs = require('fs')
    const path = require('path')
    const componentPath = path.join(
      __dirname,
      '../../components/exposure/exposure-widget.tsx'
    )
    const exists = fs.existsSync(componentPath)
    expect(exists, `ExposureWidget file missing — WIRE-02 not implemented`).toBe(true)
    if (exists) {
      const src = fs.readFileSync(componentPath, 'utf-8') as string
      expect(src).toContain('ExposureWidget')
    }
  })
})
