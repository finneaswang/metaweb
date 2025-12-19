<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import { user, showSidebar, models } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import Split from 'split.js';
	import Chart from 'chart.js/auto';

	// 心理健康组件
	import PsychologicalChat from '$lib/components/personal-data-center/PsychologicalChat.svelte';
	import PsychologicalDashboard from '$lib/components/personal-data-center/PsychologicalDashboard.svelte';
	import PsychologicalReport from '$lib/components/personal-data-center/PsychologicalReport.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let stats = {
		totalChats: 0,
		totalMessages: 0,
		totalTokens: 0,
		activeTime: 0
	};

	let assignments = [];
	let assignmentsLoading = true;
	let assignmentFilter = 'all';

	// AI Assistant state
	let aiMessages = [];
	let aiInputMessage = '';
	let aiLoading = false;
	let aiPanelCollapsed = false; // AI助手面板折叠状态

	// File upload state
	let selectedFiles = [];
	let fileInput;

	// API Configuration state - simplified to use OpenWebUI's global models
	let showModelSelector = false;
	let modelName = '';  // Selected model ID

	// Filter models from global $models store (populated at app load)
	// Only show Gemini, GPT, Claude models
	$: availableModels = $models.filter(m => {
		const id = (m.id || m.name || '').toLowerCase();
		return ['gemini', 'gpt', 'claude', 'anthropic', 'o1', 'o3'].some(p => id.includes(p));
	}).map(m => ({
		value: m.id || m.name,
		label: m.name || m.id
	}));

	// Auto-select first model if none selected
	$: if (availableModels.length > 0 && !modelName) {
		modelName = availableModels[0].value;
	}

	// Split.js instance
	let splitInstance: any = null;
	let isDesktop = false;

	// 🆕 档案文件管理状态
	let profileFiles = [];
	let activeTab = 'overview'; // 当前激活的tab: overview, profile, assignments
	let psychologicalSubTab = 'dashboard'; // 心理评估子标签: chat, dashboard, report
	let profileFilesLoading = false;
	let uploadingProfileFile = false;
	let profileFileInput;

	// 五维雷达图
	let radarChart = null;
	let radarCanvas;
	// 全部时间数据
	let radarData = {
		学术竞争力: 50,  // Academic Competitiveness
		学术韧性: 50,    // Academic Resilience
		学术协作: 50,    // Academic Collaboration
		主动学习: 50,    // 主动学习能力
		学术资本: 50     // Academic Capital
	};
	// 最近1个月数据
	let radarDataRecent = {
		学术竞争力: 50,
		学术韧性: 50,
		学术协作: 50,
		主动学习: 50,
		学术资本: 50
	};

	// 加载学术雷达数据
	const loadRadarData = async () => {
		try {
			const res = await fetch('/api/v1/pdc/academic/radar', {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (res.ok) {
				const data = await res.json();

				// 更新全部时间数据
				if (data.all_time) {
					radarData = {
						学术竞争力: data.all_time.academic_competitiveness || 50,
						学术韧性: data.all_time.academic_resilience || 50,
						学术协作: data.all_time.academic_collaboration || 50,
						主动学习: data.all_time.active_learning || 50,
						学术资本: data.all_time.academic_capital || 50
					};
				}

				// 更新最近1个月数据
				if (data.recent) {
					radarDataRecent = {
						学术竞争力: data.recent.academic_competitiveness || 50,
						学术韧性: data.recent.academic_resilience || 50,
						学术协作: data.recent.academic_collaboration || 50,
						主动学习: data.recent.active_learning || 50,
						学术资本: data.recent.academic_capital || 50
					};
				}

				// 重新渲染雷达图
				if (radarChart) {
					initRadarChart();
				}
			}
		} catch (error) {
			console.error('Failed to load radar data:', error);
		}
	};
	let selectedProfileFile = null;
	let profileFileDescription = '';
	let profileFileCategory = 'report';

	const fetchAssignments = async () => {
		assignmentsLoading = true;
		try {
			const res = await fetch(`/api/metaweb/assignments?status=${assignmentFilter === 'all' ? '' : assignmentFilter}`, {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (!res.ok) {
				throw new Error('Failed to fetch assignments');
			}

			assignments = await res.json();
		} catch (error) {
			console.error('Error fetching assignments:', error);
			toast.error($i18n.t('Failed to load assignments'));
			assignments = [];
		} finally {
			assignmentsLoading = false;
		}
	};

	const handleFileSelect = (event) => {
		const files = Array.from(event.target.files);
		selectedFiles = [...selectedFiles, ...files];
		// Reset input to allow selecting the same file again
		if (fileInput) fileInput.value = '';
	};

	const removeFile = (index) => {
		selectedFiles = selectedFiles.filter((_, i) => i !== index);
	};

	const uploadFiles = async (files) => {
		const formData = new FormData();
		files.forEach(file => {
			formData.append('files', file);
		});

		const response = await fetch('/api/metaweb/upload-files', {
			method: 'POST',
			headers: {
				Authorization: `Bearer ${localStorage.token}`
			},
			body: formData
		});

		if (!response.ok) {
			throw new Error('File upload failed');
		}

		return await response.json();
	};

	const sendAIMessage = async () => {
		if ((!aiInputMessage.trim() && selectedFiles.length === 0) || aiLoading) return;

		const userMessage = aiInputMessage.trim();
		const filesToUpload = [...selectedFiles];
		aiInputMessage = '';
		selectedFiles = [];

		let uploadedFileUrls = [];

		try {
			// Upload files first if any
			if (filesToUpload.length > 0) {
				const uploadResult = await uploadFiles(filesToUpload);
				uploadedFileUrls = uploadResult.urls || [];
			}

			// Add user message to chat with files
			const messageContent = userMessage || '请帮我分析这些文件';
			aiMessages = [...aiMessages, {
				role: 'user',
				content: messageContent,
				files: filesToUpload.map((f, i) => ({
					name: f.name,
					size: f.size,
					type: f.type,
					url: uploadedFileUrls[i]
				}))
			}];
			aiLoading = true;

			const response = await fetch('/api/metaweb/ai-assistant/chat', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({
					message: messageContent,
					files: uploadedFileUrls,
					chat_history: aiMessages.slice(0, -1), // Exclude the just-added user message
					model_name: modelName  // Selected model from dropdown
				})
			});

			if (!response.ok) {
				throw new Error('AI request failed');
			}

			const data = await response.json();

			// Add AI response to chat
			aiMessages = [...aiMessages, { role: 'assistant', content: data.response }];
		} catch (error) {
			console.error('AI Error:', error);
			toast.error('AI助手暂时无法响应，请稍后再试');
			// Remove the failed user message
			aiMessages = aiMessages.slice(0, -1);
		} finally {
			aiLoading = false;
		}
	};

	const loadChatHistory = async () => {
		try {
			const res = await fetch('/api/metaweb/ai-assistant/history', {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (res.ok) {
				const data = await res.json();
				if (data.messages && data.messages.length > 0) {
					aiMessages = data.messages.map(msg => ({
						role: msg.role,
						content: msg.content,
						files: msg.files || undefined
					}));
				}
			}
		} catch (error) {
			console.error('Error loading chat history:', error);
		}
	};

	const clearAIChat = async () => {
		try {
			const res = await fetch('/api/metaweb/ai-assistant/history', {
				method: 'DELETE',
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (res.ok) {
				aiMessages = [];
				toast.success('对话历史已清空');
			} else {
				toast.error('清空失败');
			}
		} catch (error) {
			console.error('Error clearing chat history:', error);
			toast.error('清空失败');
		}
	};

	// 🆕 ============ 档案文件管理函数 ============
	
	const loadProfileFiles = async () => {
		profileFilesLoading = true;
		try {
			const res = await fetch('/api/metaweb/ai-assistant/profile-files/list', {
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});
			if (res.ok) {
				const data = await res.json();
				profileFiles = data.files || [];
			} else {
				toast.error('加载档案文件失败');
			}
		} catch (error) {
			console.error('Load profile files error:', error);
			toast.error('加载档案文件失败');
		} finally {
			profileFilesLoading = false;
		}
	};
	
	const uploadProfileFile = async () => {
		if (!selectedProfileFile) {
			toast.error('请选择文件');
			return;
		}
		uploadingProfileFile = true;
		try {
			const formData = new FormData();
			formData.append('file', selectedProfileFile);
			formData.append('description', profileFileDescription);
			formData.append('category', profileFileCategory);
			const res = await fetch('/api/metaweb/ai-assistant/profile-files/upload', {
				method: 'POST',
				headers: { Authorization: `Bearer ${localStorage.token}` },
				body: formData
			});
			if (res.ok) {
				toast.success('档案文件上传成功！');
				selectedProfileFile = null;
				profileFileDescription = '';
				profileFileCategory = 'report';
				if (profileFileInput) profileFileInput.value = '';
				await loadProfileFiles();
			} else {
				const error = await res.json();
				toast.error(error.detail || '上传失败');
			}
		} catch (error) {
			console.error('Upload profile file error:', error);
			toast.error('上传失败');
		} finally {
			uploadingProfileFile = false;
		}
	};
	
	const deleteProfileFile = async (fileId) => {
		if (!confirm('确定删除这个档案文件吗？AI将无法再读取它。')) return;
		try {
			const res = await fetch(`/api/metaweb/ai-assistant/profile-files/${fileId}`, {
				method: 'DELETE',
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});
			if (res.ok) {
				toast.success('文件已删除');
				await loadProfileFiles();
			} else {
				toast.error('删除失败');
			}
		} catch (error) {
			console.error('Delete profile file error:', error);
			toast.error('删除失败');
		}
	};
	
	const formatFileSize = (bytes) => {
		if (bytes < 1024) return bytes + ' B';
		if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
		return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
	};
	
	const getCategoryLabel = (category) => {
		const labels = { 'report': '升学报告', 'test': '测试成绩', 'assignment': '作业', 'other': '其他' };
		return labels[category] || category;
	};

	// Load saved model preference
	const loadSavedModel = async () => {
		try {
			const res = await fetch('/api/metaweb/ai-assistant/config', {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (res.ok) {
				const config = await res.json();
				if (config && config.model_name) {
					modelName = config.model_name;
				}
			}
		} catch (error) {
			console.error('Error loading saved model:', error);
		}
	};

	// Save model preference
	const saveModelPreference = async () => {
		try {
			await fetch('/api/metaweb/ai-assistant/config', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({
					model_name: modelName,
					use_system_config: true  // Always use system config
				})
			});
			showModelSelector = false;
			toast.success('模型已更换');
		} catch (error) {
			console.error('Error saving model:', error);
			toast.error('保存失败');
		}
	};

	const handleViewportChange = (event: MediaQueryListEvent) => {
		const wasDesktop = isDesktop;
		isDesktop = event.matches;

		// Initialize or destroy Split.js based on viewport
		if (isDesktop && !wasDesktop) {
			initSplit();
		} else if (!isDesktop && wasDesktop && splitInstance) {
			splitInstance.destroy();
			splitInstance = null;
		}
	};

	const initSplit = () => {
		if (splitInstance) return;
		if (aiPanelCollapsed) return; // 折叠时不初始化

		splitInstance = Split(['#split-left', '#split-right'], {
			sizes: [60, 40],
			minSize: [300, 300],
			gutterSize: 8,
			cursor: 'col-resize',
			direction: 'horizontal'
		});
	};

	// 响应折叠状态变化
	$: if (typeof window !== 'undefined' && isDesktop) {
		if (aiPanelCollapsed && splitInstance) {
			splitInstance.destroy();
			splitInstance = null;
		} else if (!aiPanelCollapsed && !splitInstance) {
			initSplit();
		}
	}

	const initRadarChart = () => {
		if (!radarCanvas) return;

		const ctx = radarCanvas.getContext('2d');

		if (radarChart) {
			radarChart.destroy();
		}

		radarChart = new Chart(ctx, {
			type: 'radar',
			data: {
				labels: [
					'学术竞争力',
					'学术韧性',
					'学术协作',
					'主动学习',
					'学术资本'
				],
				datasets: [{
					label: '全部时间',
					data: [
						radarData.学术竞争力,
						radarData.学术韧性,
						radarData.学术协作,
						radarData.主动学习,
						radarData.学术资本
					],
					backgroundColor: 'rgba(139, 92, 246, 0.15)',
					borderColor: 'rgba(139, 92, 246, 0.8)',
					borderWidth: 2,
					pointBackgroundColor: 'rgba(139, 92, 246, 0.8)',
					pointBorderColor: '#fff',
					pointHoverBackgroundColor: '#fff',
					pointHoverBorderColor: 'rgba(139, 92, 246, 1)'
				}, {
					label: '最近1个月',
					data: [
						radarDataRecent.学术竞争力,
						radarDataRecent.学术韧性,
						radarDataRecent.学术协作,
						radarDataRecent.主动学习,
						radarDataRecent.学术资本
					],
					backgroundColor: 'rgba(59, 130, 246, 0.15)',
					borderColor: 'rgba(59, 130, 246, 1)',
					borderWidth: 2,
					pointBackgroundColor: 'rgba(59, 130, 246, 1)',
					pointBorderColor: '#fff',
					pointHoverBackgroundColor: '#fff',
					pointHoverBorderColor: 'rgba(59, 130, 246, 1)'
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: true,
				scales: {
					r: {
						beginAtZero: true,
						max: 100,
						min: 0,
						ticks: {
							stepSize: 20,
							callback: function(value) {
								return value;
							}
						},
						pointLabels: {
							font: {
								size: 11
							}
						}
					}
				},
				plugins: {
					legend: {
						display: true,
						position: 'top',
						labels: {
							usePointStyle: true,
							padding: 15,
							font: {
								size: 12
							}
						}
					},
					tooltip: {
						callbacks: {
							label: function(context) {
								return context.parsed.r + '分';
							}
						}
					}
				}
			}
		});
	};

	onMount(async () => {
		await loadProfileFiles(); // 🆕 加载档案文件
		if (!$user) {
			goto('/');
			return;
		}

		const mediaQuery = window.matchMedia('(min-width: 1024px)');
		isDesktop = mediaQuery.matches;
		mediaQuery.addEventListener('change', handleViewportChange);

		loading = false;
		await fetchAssignments();

		// Load radar data from API
		await loadRadarData();

		// Initialize radar chart
		initRadarChart();

		// Load saved model preference
		await loadSavedModel();

		// Load chat history
		await loadChatHistory();

		// Add welcome message if no history
		if (aiMessages.length === 0) {
			aiMessages = [
				{
					role: 'assistant',
					content: '你好！我是你的AI学习助手。我可以帮你分析学习情况、回答问题、提供个性化建议。有什么我可以帮你的吗？'
				}
			];
		}

		// Initialize Split.js on desktop
		if (isDesktop) {
			initSplit();
		}

		return () => {
			mediaQuery.removeEventListener('change', handleViewportChange);
		};
	});

	onDestroy(() => {
		if (splitInstance) {
			splitInstance.destroy();
		}
		if (radarChart) {
			radarChart.destroy();
		}
	});

	const formatDate = (dateString) => {
		if (!dateString) return '';
		const date = new Date(dateString);
		return date.toLocaleDateString('zh-CN', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit'
		});
	};

	const getStatusColor = (status) => {
		const colors = {
			draft: 'bg-gray-500',
			published: 'bg-green-500',
			closed: 'bg-red-500'
		};
		return colors[status] || 'bg-gray-500';
	};

	const createAssignment = () => {
		goto('/workspace/assignments/create');
	};

	const viewAssignment = (id) => {
		goto(`/workspace/assignments/${id}`);
	};
</script>

<svelte:head>
	<title>{$i18n.t('Personal Data Center')} | {$i18n.t('Open WebUI')}</title>
</svelte:head>

<div class="relative flex flex-col lg:flex-row w-full h-screen max-h-[100dvh] {$showSidebar ? 'md:max-w-[calc(100%-260px)]' : ''} max-w-full">
	<!-- Left Side: Statistics & Assignments (resizable on desktop) -->
	<div
		id="split-left"
		class="flex flex-col h-full border-r border-gray-200 dark:border-gray-700 overflow-hidden {aiPanelCollapsed ? 'w-full' : 'w-full lg:w-auto'}"
	>
		<!-- Header -->
		<div class="p-6 border-b border-gray-100 dark:border-gray-800">
			<div class="flex items-center gap-3">
				<div class="flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-blue-500">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2"
						stroke="white"
						class="w-6 h-6"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M12 3 L12 7 M12 17 L12 21 M3 12 L7 12 M17 12 L21 12 M5.2 5.2 L7.9 7.9 M16.1 16.1 L18.8 18.8 M5.2 18.8 L7.9 16.1 M16.1 7.9 L18.8 5.2 M8.5 4 L10 7 M14 17 L15.5 20 M4 8.5 L7 10 M17 14 L20 15.5"
						/>
					</svg>
				</div>
				<div>
					<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
						{$i18n.t('Personal Data Center')}
					</h1>
					<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
						{$i18n.t('View your personal data and activity statistics')}
					</p>
				</div>
			</div>
		</div>

		<!-- Tabs Navigation -->
		<div class="px-6 py-3 border-b border-gray-100 dark:border-gray-800">
			<div class="flex gap-2 text-sm font-medium">
				<button
					class="px-3 py-1.5 rounded-lg transition whitespace-nowrap {activeTab === 'overview' ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-800'}"
					on:click={() => activeTab = 'overview'}
				>
					概览
				</button>
				<button
					class="px-3 py-1.5 rounded-lg transition whitespace-nowrap {activeTab === 'profile' ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-800'}"
					on:click={() => activeTab = 'profile'}
				>
					学生档案
				</button>
				<button
					class="px-3 py-1.5 rounded-lg transition whitespace-nowrap {activeTab === 'assignments' ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-800'}"
					on:click={() => activeTab = 'assignments'}
				>
					我的作业
				</button>
				<button
					class="px-3 py-1.5 rounded-lg transition whitespace-nowrap {activeTab === 'psychological' ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-800'}"
					on:click={() => activeTab = 'psychological'}
				>
					心理评估
				</button>
			</div>
		</div>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto p-6">
			{#if loading}
				<div class="flex justify-center items-center h-64">
					<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
				</div>
			{:else}
				{#if activeTab === 'overview'}
			<!-- Statistics Cards -->
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
					<!-- Total Chats -->
					<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Total Chats')}</p>
								<p class="text-2xl font-semibold text-gray-900 dark:text-white mt-2">
									{stats.totalChats}
								</p>
							</div>
							<div class="w-12 h-12 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-blue-600 dark:text-blue-400">
									<path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
								</svg>
							</div>
						</div>
					</div>

					<!-- Total Messages -->
					<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Total Messages')}</p>
								<p class="text-2xl font-semibold text-gray-900 dark:text-white mt-2">
									{stats.totalMessages}
								</p>
							</div>
							<div class="w-12 h-12 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center">
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-green-600 dark:text-green-400">
									<path stroke-linecap="round" stroke-linejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
								</svg>
							</div>
						</div>
					</div>

					<!-- Total Tokens -->
					<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Total Tokens')}</p>
								<p class="text-2xl font-semibold text-gray-900 dark:text-white mt-2">
									{stats.totalTokens.toLocaleString()}
								</p>
							</div>
							<div class="w-12 h-12 bg-purple-100 dark:bg-purple-900 rounded-full flex items-center justify-center">
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-purple-600 dark:text-purple-400">
									<path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5m.75-9 3-3 2.148 2.148A12.061 12.061 0 0 1 16.5 7.605" />
								</svg>
							</div>
						</div>
					</div>

					<!-- Active Time -->
					<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Active Time (hrs)')}</p>
								<p class="text-2xl font-semibold text-gray-900 dark:text-white mt-2">
									{stats.activeTime}
								</p>
							</div>
							<div class="w-12 h-12 bg-orange-100 dark:bg-orange-900 rounded-full flex items-center justify-center">
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-orange-600 dark:text-orange-400">
									<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
								</svg>
							</div>
						</div>
					</div>
				</div>

				<!-- 学生五维雷达模型 -->
				<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
					<div class="mb-4">
						<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">学生五维雷达模型</h3>
						<p class="text-sm text-gray-600 dark:text-gray-400">基于行为数据的多维度能力评估</p>
					</div>

					<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
						<!-- 雷达图 -->
						<div class="lg:col-span-2">
							<div class="relative" style="height: 320px;">
								<canvas bind:this={radarCanvas}></canvas>
							</div>
						</div>

						<!-- 维度说明 -->
						<div class="space-y-3">
							<div class="bg-gradient-to-r from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 rounded-lg p-3 border-l-4 border-blue-500">
								<div class="flex items-center gap-2 mb-1">
									<div class="w-2 h-2 bg-blue-500 rounded-full"></div>
									<h4 class="font-semibold text-sm text-gray-900 dark:text-white">学术竞争力</h4>
									<span class="ml-auto text-sm font-bold text-blue-600 dark:text-blue-400">{radarData.学术竞争力}分</span>
								</div>
								<p class="text-xs text-gray-600 dark:text-gray-400">同赛道相对排名能力、击败率、竞争优势</p>
							</div>

							<div class="bg-gradient-to-r from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 rounded-lg p-3 border-l-4 border-purple-500">
								<div class="flex items-center gap-2 mb-1">
									<div class="w-2 h-2 bg-purple-500 rounded-full"></div>
									<h4 class="font-semibold text-sm text-gray-900 dark:text-white">学术韧性</h4>
									<span class="ml-auto text-sm font-bold text-purple-600 dark:text-purple-400">{radarData.学术韧性}分</span>
								</div>
								<p class="text-xs text-gray-600 dark:text-gray-400">压力下不崩溃、能恢复、能持续坚持</p>
							</div>

							<div class="bg-gradient-to-r from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 rounded-lg p-3 border-l-4 border-green-500">
								<div class="flex items-center gap-2 mb-1">
									<div class="w-2 h-2 bg-green-500 rounded-full"></div>
									<h4 class="font-semibold text-sm text-gray-900 dark:text-white">学术协作</h4>
									<span class="ml-auto text-sm font-bold text-green-600 dark:text-green-400">{radarData.学术协作}分</span>
								</div>
								<p class="text-xs text-gray-600 dark:text-gray-400">学术/项目协作完成任务，非社交能力</p>
							</div>

							<div class="bg-gradient-to-r from-orange-50 to-orange-100 dark:from-orange-900/20 dark:to-orange-800/20 rounded-lg p-3 border-l-4 border-orange-500">
								<div class="flex items-center gap-2 mb-1">
									<div class="w-2 h-2 bg-orange-500 rounded-full"></div>
									<h4 class="font-semibold text-sm text-gray-900 dark:text-white">主动学习</h4>
									<span class="ml-auto text-sm font-bold text-orange-600 dark:text-orange-400">{radarData.主动学习}分</span>
								</div>
								<p class="text-xs text-gray-600 dark:text-gray-400">资源获取、自主探索、学习系统搭建</p>
							</div>

							<div class="bg-gradient-to-r from-pink-50 to-pink-100 dark:from-pink-900/20 dark:to-pink-800/20 rounded-lg p-3 border-l-4 border-pink-500">
								<div class="flex items-center gap-2 mb-1">
									<div class="w-2 h-2 bg-pink-500 rounded-full"></div>
									<h4 class="font-semibold text-sm text-gray-900 dark:text-white">学术资本</h4>
									<span class="ml-auto text-sm font-bold text-pink-600 dark:text-pink-400">{radarData.学术资本}分</span>
								</div>
								<p class="text-xs text-gray-600 dark:text-gray-400">知识结构、方法论、经验、资源、人脉、项目沉淀</p>
							</div>
						</div>
					</div>
				</div>


				{:else if activeTab === 'profile'}
			<!-- 🆕 学生档案资料 -->
				<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
					<div class="flex justify-between items-center mb-4">
						<div class="flex items-center gap-3">
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-purple-600 dark:text-purple-400">
								<path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z" />
							</svg>
							<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
								学生档案资料
							</h2>
							<span class="text-xs text-gray-500 dark:text-gray-400">
								AI会自动读取这些背景资料
							</span>
						</div>
						<button
							class="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 hover:underline"
							on:click={() => loadProfileFiles()}
						>
							刷新
						</button>
					</div>

					<!-- 上传表单 -->
					<details class="mb-4" open>
						<summary class="cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 mb-3 flex items-center gap-2">
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
							</svg>
							上传新档案
						</summary>
						<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 space-y-3">
							<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
								<input
									type="file"
									bind:this={profileFileInput}
									on:change={(e) => { selectedProfileFile = e.target.files[0]; }}
									class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-600"
									accept=".txt,.md,.pdf,.doc,.docx,.jpg,.jpeg,.png,.json,.csv"
								/>
								<select
									bind:value={profileFileCategory}
									class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-600"
								>
									<option value="report">📋 升学报告</option>
									<option value="test">📊 测试成绩</option>
									<option value="assignment">📝 作业</option>
									<option value="other">📁 其他</option>
								</select>
							</div>
							<input
								type="text"
								bind:value={profileFileDescription}
								placeholder="文件描述（可选，例如：2024年SAT成绩单）"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-600"
							/>
							<button
								on:click={uploadProfileFile}
								disabled={!selectedProfileFile || uploadingProfileFile}
								class="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition flex items-center justify-center gap-2"
							>
								{#if uploadingProfileFile}
									<svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
										<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
										<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
									</svg>
									上传中...
								{:else}
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
										<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
									</svg>
									上传档案文件
								{/if}
							</button>
						</div>
					</details>

					<!-- 文件列表 -->
					<div class="space-y-2">
						{#if profileFilesLoading}
							<div class="text-center text-gray-400 py-8">
								<svg class="animate-spin h-8 w-8 mx-auto text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
								<p class="mt-2 text-sm">加载中...</p>
							</div>
						{:else if profileFiles.length === 0}
							<div class="text-center text-gray-400 py-8 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg">
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600">
									<path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z" />
								</svg>
								<p class="mt-3 text-sm font-medium">暂无档案文件</p>
								<p class="mt-1 text-xs">上传升学报告、测试成绩等，AI会自动了解你的背景！</p>
							</div>
						{:else}
							<div class="space-y-2">
								{#each profileFiles as file}
									<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 flex items-start justify-between border border-gray-200 dark:border-gray-600 hover:border-purple-300 dark:hover:border-purple-600 hover:shadow-sm transition">
										<div class="flex-1 min-w-0">
											<div class="flex items-center gap-2 mb-1">
												<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-gray-400 flex-shrink-0">
													<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
												</svg>
												<span class="font-medium text-gray-900 dark:text-white text-sm truncate">{file.file_name}</span>
												<span class="px-2 py-0.5 bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300 rounded text-xs flex-shrink-0">
													{getCategoryLabel(file.category)}
												</span>
											</div>
											{#if file.description}
												<p class="text-xs text-gray-600 dark:text-gray-400 mb-1">{file.description}</p>
											{/if}
											<div class="flex items-center gap-2 text-xs text-gray-400">
												<span>{formatFileSize(file.file_size)}</span>
												<span>•</span>
												<span>{new Date(file.created_at).toLocaleDateString('zh-CN')}</span>
											</div>
										</div>
										<button
											on:click={() => deleteProfileFile(file.id)}
											class="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition flex-shrink-0"
											title="删除文件"
										>
											<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
												<path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
											</svg>
										</button>
									</div>
								{/each}
							</div>
						{/if}
					</div>
				</div>

				{:else if activeTab === 'assignments'}
			<!-- Assignments Section -->
				<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
					<div class="flex justify-between items-center mb-4">
						<div class="flex items-center gap-3">
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-gray-700 dark:text-gray-300">
								<path stroke-linecap="round" stroke-linejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" />
							</svg>
							<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
								{$i18n.t('Assignments')}
							</h2>
						</div>

						{#if $user?.role === 'teacher' || $user?.role === 'leader' || $user?.role === 'admin'}
							<button
								class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition flex items-center gap-2"
								on:click={createAssignment}
							>
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
									<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
								</svg>
								{$i18n.t('Create Assignment')}
							</button>
						{/if}
					</div>

					<div class="flex gap-2 mb-4 flex-wrap">
						<button
							class="px-4 py-2 rounded-lg transition {assignmentFilter === 'all'
								? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300'
								: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}"
							on:click={() => { assignmentFilter = 'all'; fetchAssignments(); }}
						>
							{$i18n.t('All')}
						</button>
						{#if $user?.role === 'teacher' || $user?.role === 'leader' || $user?.role === 'admin'}
							<button
								class="px-4 py-2 rounded-lg transition {assignmentFilter === 'draft'
									? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300'
									: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}"
								on:click={() => { assignmentFilter = 'draft'; fetchAssignments(); }}
							>
								{$i18n.t('Draft')}
							</button>
						{/if}
						<button
							class="px-4 py-2 rounded-lg transition {assignmentFilter === 'published'
								? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300'
								: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}"
							on:click={() => { assignmentFilter = 'published'; fetchAssignments(); }}
						>
							{$i18n.t('Published')}
						</button>
						<button
							class="px-4 py-2 rounded-lg transition {assignmentFilter === 'closed'
								? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300'
								: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}"
							on:click={() => { assignmentFilter = 'closed'; fetchAssignments(); }}
						>
							{$i18n.t('Closed')}
						</button>
					</div>

					{#if assignmentsLoading}
						<div class="flex justify-center items-center py-12">
							<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
						</div>
					{:else if assignments.length === 0}
						<div class="flex flex-col items-center justify-center py-12 text-gray-500">
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-16 h-16 mb-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" />
							</svg>
							<p class="text-lg">{$i18n.t('No assignments found')}</p>
							{#if $user?.role === 'teacher' || $user?.role === 'leader' || $user?.role === 'admin'}
								<button class="mt-4 text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300" on:click={createAssignment}>
									{$i18n.t('Create your first assignment')}
								</button>
							{/if}
						</div>
					{:else}
						<div class="grid grid-cols-1 gap-4">
							{#each assignments as assignment}
								<div
									class="bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-lg transition cursor-pointer"
									on:click={() => viewAssignment(assignment.id)}
									on:keydown={(e) => { if (e.key === 'Enter') viewAssignment(assignment.id); }}
									role="button"
									tabindex="0"
								>
									<div class="p-4">
										<div class="flex justify-between items-start mb-3">
											<h3 class="text-lg font-semibold text-gray-900 dark:text-white line-clamp-1">
												{assignment.title}
											</h3>
											<span class="px-2 py-1 text-xs text-white rounded-full {getStatusColor(assignment.status)}">
												{$i18n.t(assignment.status)}
											</span>
										</div>
										<p class="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-1">
											{assignment.description || $i18n.t('No description')}
										</p>
										<div class="flex gap-4 text-sm text-gray-500 dark:text-gray-400">
											<div class="flex items-center gap-2">
												<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
													<path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
												</svg>
												<span>{formatDate(assignment.due_date)}</span>
											</div>
											<div class="flex items-center gap-2">
												<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
													<path stroke-linecap="round" stroke-linejoin="round" d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
												</svg>
												<span>{assignment.total_points} pts</span>
											</div>
										</div>
									</div>
								</div>
							{/each}
						</div>
					{/if}
				</div>

				<!-- 心理评估 Tab -->
				{:else if activeTab === 'psychological'}
					<div class="space-y-4">
						<!-- 子标签导航 -->
						<div class="flex gap-2 border-b border-gray-200 dark:border-gray-700 pb-2">
							<button
								class="px-4 py-2 rounded-lg transition {psychologicalSubTab === 'dashboard' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
								on:click={() => psychologicalSubTab = 'dashboard'}
							>
								数据概览
							</button>
							<button
								class="px-4 py-2 rounded-lg transition {psychologicalSubTab === 'chat' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
								on:click={() => psychologicalSubTab = 'chat'}
							>
								AI聊天
							</button>
							<button
								class="px-4 py-2 rounded-lg transition {psychologicalSubTab === 'report' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
								on:click={() => psychologicalSubTab = 'report'}
							>
								历史报告
							</button>
						</div>

						<!-- 子标签内容 -->
						{#if psychologicalSubTab === 'chat'}
							<PsychologicalChat />
						{:else if psychologicalSubTab === 'dashboard'}
							<PsychologicalDashboard />
						{:else if psychologicalSubTab === 'report'}
							<PsychologicalReport />
						{/if}
					</div>

			{/if}
			{/if}
		</div>
	</div>

	<!-- 折叠时的悬浮展开按钮 -->
	{#if aiPanelCollapsed}
		<button
			on:click={() => { aiPanelCollapsed = false; }}
			class="hidden lg:block fixed top-4 right-4 z-50 p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg transition"
			title="展开AI助手"
		>
			<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
				<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
			</svg>
		</button>
	{/if}

	<!-- Right Side: AI Assistant -->
	<div
		id="split-right"
		class="{aiPanelCollapsed ? 'hidden' : 'hidden lg:flex'} flex-col h-full bg-white dark:bg-gray-900 overflow-hidden transition-all duration-300"
	>

		<!-- AI Header -->
		<div class="px-3 py-2.5 border-b border-gray-100 dark:border-gray-800">
			<div class="flex items-center justify-between">
					<div class="flex items-center gap-2">
						<div class="w-7 h-7 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="white" class="w-3.5 h-3.5">
								<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
							</svg>
						</div>
						<div class="min-w-0">
							<h2 class="text-sm font-medium text-gray-900 dark:text-white leading-tight">AI学习助手</h2>
							<p class="text-xs text-gray-500 dark:text-gray-400 leading-tight mt-0.5">基于你的学习数据提供建议</p>
						</div>
					</div>
					<div class="flex items-center gap-1">
					<button
						on:click={() => { aiPanelCollapsed = !aiPanelCollapsed; }}
						class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition flex-shrink-0"
						title={aiPanelCollapsed ? "展开AI助手" : "折叠AI助手"}
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4 text-gray-600 dark:text-gray-400">
							{#if aiPanelCollapsed}
								<path stroke-linecap="round" stroke-linejoin="round" d="M18.75 19.5l-7.5-7.5 7.5-7.5m-6 15L5.25 12l7.5-7.5" />
							{:else}
								<path stroke-linecap="round" stroke-linejoin="round" d="M11.25 4.5l7.5 7.5-7.5 7.5m-6-15l7.5 7.5-7.5 7.5" />
							{/if}
						</svg>
					</button>
					<button
						on:click={() => { showModelSelector = !showModelSelector; }}
						class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition flex-shrink-0"
						title="选择模型"
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4 text-gray-600 dark:text-gray-400">
							<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
						</svg>
					</button>
					<button
						on:click={clearAIChat}
						class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition flex-shrink-0"
						title="清空对话"
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4 text-gray-600 dark:text-gray-400">
							<path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
						</svg>
					</button>
					</div>
				</div>
		</div>

		<!-- Chat Messages -->
		<div class="flex-1 overflow-y-auto px-3 py-4">
			<div class="space-y-5">
				{#each aiMessages as message}
					<div class="flex w-full {message.role === 'user' ? 'justify-end' : 'justify-start'} group">
						{#if message.role === 'assistant'}
							<!-- Assistant Avatar -->
							<div class="flex-shrink-0 mr-3">
								<div class="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="white" class="w-4 h-4">
										<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
									</svg>
								</div>
							</div>
							<!-- Assistant Message Bubble -->
							<div class="flex-1 max-w-[85%]">
								<div class="text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap leading-relaxed">
									{message.content}
								</div>
							</div>
						{:else}
							<!-- User Message Bubble -->
							<div class="max-w-[85%] bg-gray-50 dark:bg-gray-850 rounded-3xl px-4 py-2.5">
								<!-- Files if any -->
								{#if message.files && message.files.length > 0}
									<div class="mb-2 space-y-1">
										{#each message.files as file}
											<div class="flex items-center gap-2 text-xs bg-white dark:bg-gray-800 rounded-lg px-2 py-1.5">
												<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-gray-500">
													<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
												</svg>
												<span class="text-gray-700 dark:text-gray-300 truncate flex-1">{file.name}</span>
												<span class="text-gray-500">({(file.size / 1024).toFixed(1)}KB)</span>
											</div>
										{/each}
									</div>
								{/if}
								<p class="text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap leading-relaxed">{message.content}</p>
							</div>
						{/if}
					</div>
				{/each}

				{#if aiLoading}
					<div class="flex w-full justify-start group">
						<div class="flex-shrink-0 mr-3">
							<div class="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="white" class="w-4 h-4">
									<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
								</svg>
							</div>
						</div>
						<div class="flex-1">
							<div class="flex gap-1.5 items-center">
								<div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
								<div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
								<div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
							</div>
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- Input Area -->
		<div class="px-4 pb-4">
			<div class="bg-gray-50 dark:bg-gray-850 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-sm">
				<!-- File Preview Area -->
				{#if selectedFiles.length > 0}
					<div class="px-3 pt-2 pb-1">
						<div class="space-y-1">
							{#each selectedFiles as file, index}
								<div class="flex items-center gap-2 bg-white dark:bg-gray-800 rounded-lg px-2 py-1.5 text-xs">
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-blue-500">
										<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
									</svg>
									<span class="text-gray-700 dark:text-gray-300 truncate flex-1">{file.name}</span>
									<span class="text-gray-500">({(file.size / 1024).toFixed(1)}KB)</span>
									<button
										type="button"
										on:click={() => removeFile(index)}
										class="p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
									>
										<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-3.5 h-3.5 text-gray-500">
											<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
										</svg>
									</button>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<form on:submit|preventDefault={sendAIMessage}>
					<div class="flex items-end gap-2 p-2">
						<!-- File Upload Button -->
						<input
							type="file"
							bind:this={fileInput}
							on:change={handleFileSelect}
							multiple
							accept="image/*,.pdf,.doc,.docx,.txt,.md"
							class="hidden"
						/>
						<button
							type="button"
							on:click={() => fileInput?.click()}
							disabled={aiLoading}
							class="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition disabled:opacity-50"
							title="上传文件"
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4 text-gray-600 dark:text-gray-400">
								<path stroke-linecap="round" stroke-linejoin="round" d="m18.375 12.739-7.693 7.693a4.5 4.5 0 0 1-6.364-6.364l10.94-10.94A3 3 0 1 1 19.5 7.372L8.552 18.32m.009-.01-.01.01m5.699-9.941-7.81 7.81a1.5 1.5 0 0 0 2.112 2.13" />
							</svg>
						</button>

						<textarea
							bind:value={aiInputMessage}
							placeholder="问我任何关于学习的问题..."
							class="flex-1 px-3 py-2 bg-transparent outline-none resize-none text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 max-h-32"
							rows="1"
							disabled={aiLoading}
							on:input={(e) => {
								e.target.style.height = 'auto';
								e.target.style.height = e.target.scrollHeight + 'px';
							}}
							on:keydown={(e) => {
								if (e.key === 'Enter' && !e.shiftKey) {
									e.preventDefault();
									sendAIMessage();
								}
							}}
						/>
						<button
							type="submit"
							disabled={(!aiInputMessage.trim() && selectedFiles.length === 0) || aiLoading}
							class="p-2 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed dark:bg-white dark:hover:bg-gray-100 dark:disabled:bg-gray-700 text-white dark:text-gray-900 rounded-full transition flex items-center justify-center"
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
							</svg>
						</button>
					</div>
				</form>

				<!-- Quick Actions -->
				<div class="flex gap-1.5 px-3 pb-2.5 flex-wrap">
					<button
						on:click={() => { aiInputMessage = '我最近的学习情况怎么样？'; sendAIMessage(); }}
						class="px-3 py-1 text-xs bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition border border-gray-200 dark:border-gray-700"
						disabled={aiLoading}
					>
						分析学习情况
					</button>
					<button
						on:click={() => { aiInputMessage = '给我一些学习建议'; sendAIMessage(); }}
						class="px-3 py-1 text-xs bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition border border-gray-200 dark:border-gray-700"
						disabled={aiLoading}
					>
						学习建议
					</button>
				</div>
			</div>
		</div>
	</div>
</div>

<!-- Model Selector Modal -->
{#if showModelSelector}
	<div class="fixed inset-0 bg-black/30 dark:bg-black/60 backdrop-blur-xl backdrop-saturate-150 flex items-center justify-center z-50 p-4" on:click={() => { showModelSelector = false; }}>
		<div class="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-md w-full" on:click|stopPropagation>
			<!-- Modal Header -->
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
				<div class="flex items-center justify-between">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white">选择 AI 模型</h3>
					<button
						on:click={() => { showModelSelector = false; }}
						class="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
							<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
			</div>

			<!-- Modal Body -->
			<div class="px-6 py-4">
				{#if availableModels.length === 0}
					<div class="text-center py-8">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-12 h-12 mx-auto text-gray-400 mb-3">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
						</svg>
						<p class="text-gray-600 dark:text-gray-400">暂无可用模型</p>
						<p class="text-sm text-gray-500 dark:text-gray-500 mt-1">请联系管理员配置 AI 连接</p>
					</div>
				{:else}
					<div class="space-y-2 max-h-64 overflow-y-auto">
						{#each availableModels as model}
							<button
								on:click={() => { modelName = model.value; saveModelPreference(); }}
								class="w-full text-left px-4 py-3 rounded-lg border transition {modelName === model.value ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-500' : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'}"
							>
								<div class="flex items-center justify-between">
									<span class="text-sm font-medium text-gray-900 dark:text-white">{model.label}</span>
									{#if modelName === model.value}
										<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5 text-blue-600">
											<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
										</svg>
									{/if}
								</div>
							</button>
						{/each}
					</div>
					<p class="mt-3 text-xs text-gray-500 dark:text-gray-400 text-center">
						共 {availableModels.length} 个可用模型
					</p>
				{/if}
			</div>
		</div>
	</div>
{/if}

<style>
	/* Split.js gutter styling */
	:global(.gutter) {
		background-color: rgb(229, 231, 235);
		background-repeat: no-repeat;
		background-position: 50%;
	}

	:global(.gutter.gutter-horizontal) {
		background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAeCAYAAADkftS9AAAAIklEQVQoU2M4c+bMfxAGAgYYmwGrIIiDjrELjpo5aiZeMwF+yNnOs5KSvgAAAABJRU5ErkJggg==');
		cursor: col-resize;
	}

	:global(.gutter:hover) {
		background-color: rgb(147, 197, 253);
	}

	:global(html.dark .gutter) {
		background-color: rgb(55, 65, 81);
	}

	:global(html.dark .gutter:hover) {
		background-color: rgb(59, 130, 246);
	}

	/* Custom gray-850 color for dark mode chat bubbles (OpenWebUI style) */
	:global(.dark .bg-gray-850) {
		background-color: #262626;
	}

	/* Ensure smooth transitions for textarea auto-resize */
	textarea {
		transition: none;
	}
</style>
