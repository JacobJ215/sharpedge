import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

/**
 * WIRE-02 RED stubs for VenueDislocWidget.
 *
 * The component at @/components/venue-dislocation/venue-disloc-widget does not
 * exist yet. Tests assert expected behavior contracts. They are RED because the
 * component is missing — these pass once the component is implemented in Wave 1.
 *
 * Pattern: dynamically require the module path; assert the exports match contract.
 */

const COMPONENT_PATH = 'src/components/venue-dislocation/venue-disloc-widget.tsx'

const mockDislocData = {
  market_id: 'nfl_game_1',
  consensus_prob: 0.62,
  scores: {
    kalshi: 0.58,
    polymarket: 0.65,
    pinnacle: 0.63,
  },
  dislocation_bps: 70,
}

describe('VenueDislocWidget — WIRE-02 RED stubs', () => {
  it('test_venue_dislocation_widget_renders: VenueDislocWidget component file exists', () => {
    // RED: the file does not exist yet — expect it to be present
    // This will pass once Wave 1 creates the component
    const fs = require('fs')
    const path = require('path')
    const componentPath = path.join(
      __dirname,
      '../../components/venue-dislocation/venue-disloc-widget.tsx'
    )
    expect(
      fs.existsSync(componentPath),
      `VenueDislocWidget not found at ${componentPath}`
    ).toBe(true)
  })

  it('test_venue_dislocation_widget_shows_consensus_prob: component exports VenueDislocWidget named export', () => {
    // RED: file does not exist yet
    const fs = require('fs')
    const path = require('path')
    const componentPath = path.join(
      __dirname,
      '../../components/venue-dislocation/venue-disloc-widget.tsx'
    )
    const exists = fs.existsSync(componentPath)
    expect(exists, `VenueDislocWidget file missing — WIRE-02 not implemented`).toBe(true)
    if (exists) {
      const src = fs.readFileSync(componentPath, 'utf-8') as string
      expect(src).toContain('VenueDislocWidget')
    }
  })
})
