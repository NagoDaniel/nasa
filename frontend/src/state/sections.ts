export type Role = 'farmer' | 'procurement'

export const SECTIONS = {
  farmer: ['overview', 'weather', 'risks', 'soil', 'crops', 'rotations'],
  procurement: ['sourcing', 'recs', 'trends'],
} as const

export type FarmerSection = (typeof SECTIONS.farmer)[number]
export type ProcurementSection = (typeof SECTIONS.procurement)[number]
export type Section = FarmerSection | ProcurementSection
