/**
 * Camelot wheel color mapping for key display.
 */
const CAMELOT_COLORS: Record<string, string> = {
	'1A': '#f44336', '1B': '#ff7043',
	'2A': '#ff5722', '2B': '#ff9800',
	'3A': '#ff9800', '3B': '#ffc107',
	'4A': '#ffc107', '4B': '#ffeb3b',
	'5A': '#cddc39', '5B': '#8bc34a',
	'6A': '#4caf50', '6B': '#66bb6a',
	'7A': '#009688', '7B': '#26a69a',
	'8A': '#00bcd4', '8B': '#29b6f6',
	'9A': '#2196f3', '9B': '#42a5f5',
	'10A': '#3f51b5', '10B': '#5c6bc0',
	'11A': '#673ab7', '11B': '#7e57c2',
	'12A': '#9c27b0', '12B': '#e91e63',
};

export function getCamelotColor(key: string | null): string {
	if (!key) return '#666';
	return CAMELOT_COLORS[key.toUpperCase()] ?? '#888';
}
