<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Network } from 'vis-network/standalone';

	// Props
	export let graphData = { nodes: [], edges: [] };
	export let selectedNode = null;

	let container;
	let network = null;
	let transformedData = null;

	// Difficulty color mapping
	const getDifficultyColor = (level) => {
		const colors = {
			1: { background: '#4CAF50', border: '#388E3C', highlight: { background: '#66BB6A', border: '#2E7D32' } },
			2: { background: '#8BC34A', border: '#689F38', highlight: { background: '#9CCC65', border: '#558B2F' } },
			3: { background: '#FFC107', border: '#FFA000', highlight: { background: '#FFD54F', border: '#FF8F00' } },
			4: { background: '#FF9800', border: '#F57C00', highlight: { background: '#FFB74D', border: '#E65100' } },
			5: { background: '#F44336', border: '#D32F2F', highlight: { background: '#E57373', border: '#C62828' } }
		};
		return colors[level] || colors[3];
	};

	// Mastery level border color (for students)
	const getMasteryBorderColor = (masteryLevel) => {
		if (masteryLevel === null || masteryLevel === undefined) return '#BDBDBD'; // Gray - not learned
		if (masteryLevel < 0.5) return '#FFC107'; // Yellow - learning
		if (masteryLevel < 0.8) return '#2196F3'; // Blue - basic mastery
		return '#4CAF50'; // Green - fully mastered
	};

	// Transform API data to vis-network format
	const transformData = (data) => {
		const visNodes = data.nodes.map((node, index) => {
			const difficulty = node.difficulty_level || 3;
			const color = getDifficultyColor(difficulty);

			// If mastery_level exists (student view), use thicker colored border
			const borderWidth = node.mastery_level !== undefined ? 4 : 2;
			const borderColor = node.mastery_level !== undefined
				? getMasteryBorderColor(node.mastery_level)
				: color.border;

			return {
				id: node.id,
				label: node.label,
				title: `${node.label}\n科目: ${node.subject}\n难度: ${difficulty}/5${node.mastery_level !== undefined ? `\n掌握度: ${(node.mastery_level * 100).toFixed(0)}%` : ''}`,
				level: difficulty, // For hierarchical layout
				color: {
					background: color.background,
					border: borderColor,
					highlight: color.highlight
				},
				borderWidth,
				font: { size: 14, color: '#212121', bold: { color: '#000000' } },
				shape: 'box',
				margin: 10,
				widthConstraint: { minimum: 80, maximum: 150 },
				// Store original data and colors
				originalData: node,
				originalColor: color,
				originalBorderWidth: borderWidth,
				originalBorderColor: borderColor
			};
		});

		const visEdges = data.edges.map((edge, index) => {
			const isPrerequisite = edge.relation_type === 'prerequisite';

			return {
				id: `edge_${index}`,
				from: data.nodes.find(n => n.label === edge.from_node)?.id,
				to: data.nodes.find(n => n.label === edge.to_node)?.id,
				arrows: isPrerequisite ? 'to' : '',
				dashes: !isPrerequisite,
				color: {
					color: isPrerequisite ? '#424242' : '#9E9E9E',
					highlight: isPrerequisite ? '#000000' : '#616161'
				},
				width: isPrerequisite ? 2 : 1,
				smooth: { type: 'cubicBezier', roundness: 0.5 },
				// Store original properties
				originalColor: isPrerequisite ? '#424242' : '#9E9E9E',
				originalWidth: isPrerequisite ? 2 : 1
			};
		}).filter(edge => edge.from && edge.to); // Filter out invalid edges

		return { nodes: visNodes, edges: visEdges };
	};

	// Network options
	const options = {
		layout: {
			hierarchical: {
				enabled: true,
				direction: 'UD',
				sortMethod: 'directed',
				levelSeparation: 150,
				nodeSpacing: 120,
				treeSpacing: 200
			}
		},
		physics: {
			enabled: true,
			hierarchicalRepulsion: {
				centralGravity: 0.0,
				springLength: 100,
				springConstant: 0.01,
				nodeDistance: 150,
				damping: 0.09
			},
			stabilization: {
				enabled: true,
				iterations: 100
			}
		},
		interaction: {
			dragNodes: true,
			dragView: true,
			zoomView: true,
			hover: true,
			tooltipDelay: 200,
			selectConnectedEdges: true,
			navigationButtons: false
		},
		nodes: {
			shadow: {
				enabled: true,
				color: 'rgba(0,0,0,0.2)',
				size: 5,
				x: 2,
				y: 2
			}
		},
		edges: {
			shadow: {
				enabled: false
			}
		}
	};

	onMount(() => {
		if (container && graphData) {
			transformedData = transformData(graphData);
			network = new Network(container, transformedData, options);

			// Event listeners
			network.on('click', (params) => {
				if (params.nodes.length > 0) {
					const nodeId = params.nodes[0];
					const node = transformedData.nodes.find(n => n.id === nodeId);
					if (node) {
						selectedNode = node.originalData;
					}
				} else {
					selectedNode = null;
				}
			});

			network.on('doubleClick', (params) => {
				if (params.nodes.length > 0) {
					network.focus(params.nodes[0], {
						scale: 1.5,
						animation: {
							duration: 500,
							easingFunction: 'easeInOutQuad'
						}
					});
				}
			});

			// Disable physics after stabilization for better performance
			network.once('stabilizationIterationsDone', () => {
				network.setOptions({ physics: false });
			});
		}
	});

	onDestroy(() => {
		if (network) {
			network.destroy();
		}
	});

	// Export functions
	export const fitView = () => {
		if (network) {
			network.fit({
				animation: {
					duration: 500,
					easingFunction: 'easeInOutQuad'
				}
			});
		}
	};

	export const resetLayout = () => {
		if (network) {
			network.setOptions({ physics: true });
			network.stabilize();
			setTimeout(() => {
				network.setOptions({ physics: false });
			}, 2000);
		}
	};

	export const highlightPath = (nodePath) => {
		if (!network || !nodePath || nodePath.length === 0 || !transformedData) return;

		const allNodes = transformedData.nodes;
		const allEdges = transformedData.edges;

		// Get path node IDs
		const pathNodeIds = nodePath.map(label =>
			graphData.nodes.find(n => n.label === label)?.id
		).filter(id => id);

		// Build edge map for path highlighting
		const pathEdges = [];
		for (let i = 0; i < pathNodeIds.length - 1; i++) {
			const fromId = pathNodeIds[i];
			const toId = pathNodeIds[i + 1];

			// Find edge between consecutive nodes in path
			const edge = allEdges.find(e =>
				(e.from === fromId && e.to === toId) ||
				(e.from === toId && e.to === fromId)
			);
			if (edge) pathEdges.push(edge.id);
		}

		// Update all nodes - dim non-path nodes
		allNodes.forEach((node, index) => {
			const isInPath = pathNodeIds.includes(node.id);
			const pathIndex = pathNodeIds.indexOf(node.id);

			if (isInPath) {
				// Highlight path node with glow effect
				network.body.data.nodes.update({
					id: node.id,
					opacity: 1.0,
					borderWidth: 6,
					color: {
						background: node.originalColor.background,
						border: '#FF4081', // Pink highlight for path
						highlight: node.originalColor.highlight
					},
					font: {
						size: 16,
						color: '#000000',
						bold: { color: '#000000' }
					},
					// Add order number label
					label: `${pathIndex + 1}. ${node.label}`,
					shadow: {
						enabled: true,
						color: 'rgba(255, 64, 129, 0.5)',
						size: 15,
						x: 0,
						y: 0
					}
				});
			} else {
				// Dim non-path node
				network.body.data.nodes.update({
					id: node.id,
					opacity: 0.25,
					color: {
						background: '#E0E0E0',
						border: '#BDBDBD',
						highlight: node.originalColor.highlight
					},
					font: {
						size: 14,
						color: '#757575'
					}
				});
			}
		});

		// Update all edges - highlight path edges
		allEdges.forEach(edge => {
			const isInPath = pathEdges.includes(edge.id);

			if (isInPath) {
				// Highlight path edge
				network.body.data.edges.update({
					id: edge.id,
					color: {
						color: '#FF4081',
						highlight: '#FF4081'
					},
					width: 4,
					opacity: 1.0
				});
			} else {
				// Dim non-path edge
				network.body.data.edges.update({
					id: edge.id,
					color: {
						color: '#E0E0E0',
						highlight: edge.originalColor
					},
					width: 1,
					opacity: 0.2
				});
			}
		});

		// Focus on the path
		if (pathNodeIds.length > 0) {
			setTimeout(() => {
				network.fit({
					nodes: pathNodeIds,
					animation: {
						duration: 800,
						easingFunction: 'easeInOutQuad'
					}
				});
			}, 100);
		}
	};

	export const clearHighlight = () => {
		if (!network || !transformedData) return;

		const allNodes = transformedData.nodes;
		const allEdges = transformedData.edges;

		// Restore all nodes to original state
		allNodes.forEach(node => {
			network.body.data.nodes.update({
				id: node.id,
				opacity: 1.0,
				borderWidth: node.originalBorderWidth,
				color: {
					background: node.originalColor.background,
					border: node.originalBorderColor,
					highlight: node.originalColor.highlight
				},
				font: {
					size: 14,
					color: '#212121',
					bold: { color: '#000000' }
				},
				// Remove order number
				label: node.label,
				shadow: {
					enabled: true,
					color: 'rgba(0,0,0,0.2)',
					size: 5,
					x: 2,
					y: 2
				}
			});
		});

		// Restore all edges to original state
		allEdges.forEach(edge => {
			network.body.data.edges.update({
				id: edge.id,
				color: {
					color: edge.originalColor,
					highlight: edge.originalColor
				},
				width: edge.originalWidth,
				opacity: 1.0
			});
		});

		// Fit view
		setTimeout(() => {
			fitView();
		}, 100);
	};
</script>

<div bind:this={container} class="knowledge-graph-container" />

<style>
	.knowledge-graph-container {
		width: 100%;
		height: 600px;
		border: 1px solid #e0e0e0;
		border-radius: 8px;
		background: #fafafa;
		position: relative;
	}

	:global(.dark) .knowledge-graph-container {
		background: #1a1a1a;
		border-color: #424242;
	}
</style>
