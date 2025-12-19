<script lang="ts">
	import { onMount } from 'svelte';
	import { user, models } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { generateOpenAIChatCompletion } from '$lib/apis/openai';

	// 心理咨询AI模型 - 从全局模型列表中选择
	let selectedModel = '';

	// 心理咨询系统提示词
	const SYSTEM_PROMPT = `你是一位温暖、专业的学校心理咨询师。你的任务是：
1. 倾听学生的困扰和压力
2. 提供情绪支持和建设性建议
3. 识别学生的情绪状态（愉快/平静/焦虑/低落）
4. 评估压力水平（1-5级）
5. 关注睡眠和生活习惯

对话风格：
- 温暖、共情、非评判性
- 提出开放式问题鼓励学生表达
- 适时提供心理健康知识
- 如发现严重心理问题，建议寻求专业帮助

请用中文回复，语气亲切自然。`;

	// 聊天时长追踪
	let chatStartTime = null;
	let sessionDuration = 0;
	let weeklyDuration = 0;
	let weeklyTarget = 600;
	let timerInterval;

	// 心理数据
	let psychologicalData = {
		weekly_chat_duration: 0,
		last_chat_date: null,
		mood_summary: '',
		stress_level: 0,
		sleep_quality: '',
		ai_suggestions: ''
	};

	// AI对话状态
	let messages = [];
	let inputMessage = '';
	let isLoading = false;
	let chatContainer;

	// 加载用户心理数据（从 PostgreSQL）
	const loadPsychologicalData = async () => {
		try {
			const res = await fetch('/api/v1/pdc/psychological/data', {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (res.ok) {
				const data = await res.json();
				if (data) {
					psychologicalData = {
						...psychologicalData,
						...data
					};
					weeklyDuration = psychologicalData.weekly_chat_duration || 0;
				}
			}
		} catch (error) {
			console.error('Failed to load psychological data:', error);
		}
	};

	// 保存聊天时长到 PostgreSQL
	const saveChatDuration = async () => {
		try {
			const totalDuration = weeklyDuration + sessionDuration;
			await fetch('/api/v1/pdc/psychological/data', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({
					weekly_chat_duration: totalDuration,
					last_chat_date: new Date().toISOString().split('T')[0]
				})
			});
			weeklyDuration = totalDuration;
		} catch (error) {
			console.error('Failed to save chat duration:', error);
		}
	};

	// 保存聊天记录到 PostgreSQL
	const saveChatHistory = async () => {
		if (messages.length <= 1) return; // 只有初始消息时不保存

		try {
			await fetch('/api/v1/pdc/psychological/chats', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({
					messages: messages,
					session_duration: sessionDuration
				})
			});
		} catch (error) {
			console.error('Failed to save chat history:', error);
		}
	};

	// 启动计时器
	const startChatTimer = () => {
		if (!chatStartTime) {
			chatStartTime = Date.now();
			timerInterval = setInterval(() => {
				sessionDuration = Math.floor((Date.now() - chatStartTime) / 1000);
				if (sessionDuration % 30 === 0 && sessionDuration > 0) {
					saveChatDuration();
				}
			}, 1000);
		}
	};

	// 停止计时器
	const stopChatTimer = () => {
		if (timerInterval) {
			clearInterval(timerInterval);
			timerInterval = null;
		}
		if (sessionDuration > 0) {
			saveChatDuration();
			saveChatHistory();
		}
	};

	// 格式化时间显示
	const formatTime = (seconds) => {
		const mins = Math.floor(seconds / 60);
		const secs = seconds % 60;
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	};

	// 滚动到底部
	const scrollToBottom = () => {
		if (chatContainer) {
			setTimeout(() => {
				chatContainer.scrollTop = chatContainer.scrollHeight;
			}, 100);
		}
	};

	// 发送消息到AI
	const sendMessage = async () => {
		if (!inputMessage.trim()) return;

		const userMessage = {
			role: 'user',
			content: inputMessage
		};

		messages = [...messages, userMessage];
		const currentInput = inputMessage;
		inputMessage = '';
		isLoading = true;
		scrollToBottom();

		// 启动计时器
		startChatTimer();

		try {
			// 构建发送给API的消息列表（包含系统提示）
			const apiMessages = [
				{ role: 'system', content: SYSTEM_PROMPT },
				...messages
			];

			const response = await generateOpenAIChatCompletion(
				localStorage.token,
				{
					model: selectedModel || 'gpt-4o-mini',
					messages: apiMessages,
					stream: false
				}
			);

			if (response && response.choices && response.choices[0]) {
				const aiMessage = {
					role: 'assistant',
					content: response.choices[0].message.content
				};
				messages = [...messages, aiMessage];
			} else {
				throw new Error('Invalid response from AI');
			}
		} catch (error) {
			console.error('Failed to send message:', error);
			toast.error('发送消息失败，请稍后重试');
			// 移除刚才添加的用户消息
			messages = messages.slice(0, -1);
			inputMessage = currentInput;
		} finally {
			isLoading = false;
			scrollToBottom();
		}
	};

	// 快速情绪选择
	const selectMood = (mood) => {
		inputMessage = `今天我感觉${mood}`;
	};

	// 处理回车发送
	const handleKeydown = (e) => {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	};

	onMount(() => {
		loadPsychologicalData();

		// 初始化AI对话
		messages = [
			{
				role: 'assistant',
				content: '你好！我是你的心理健康助手。在这里，你可以安全地分享你的感受、压力和困扰。我会倾听并提供支持。你今天过得怎么样？'
			}
		];

		return () => {
			stopChatTimer();
		};
	});

	// 自动选择合适的心理咨询模型（优先选择 GPT-4/Claude）
	$: availablePsychModels = $models.filter(m => {
		const id = (m.id || m.name || '').toLowerCase();
		return ['gpt-4', 'gpt-5', 'claude', 'gemini'].some(p => id.includes(p));
	});

	$: if (availablePsychModels.length > 0 && !selectedModel) {
		// 优先选择 GPT-4o 或 Claude
		const preferred = availablePsychModels.find(m =>
			(m.id || '').toLowerCase().includes('gpt-4o') ||
			(m.id || '').toLowerCase().includes('claude')
		);
		selectedModel = preferred ? (preferred.id || preferred.name) : (availablePsychModels[0].id || availablePsychModels[0].name);
	}

	// 计算进度百分比
	$: totalDuration = weeklyDuration + sessionDuration;
	$: progress = Math.min((totalDuration / weeklyTarget) * 100, 100);
	$: isTargetMet = totalDuration >= weeklyTarget;
</script>

<div class="h-full flex flex-col">
	<!-- 顶部进度条 -->
	<div class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4">
		<div class="max-w-4xl mx-auto">
			<div class="flex items-center justify-between mb-2">
				<div class="flex items-center gap-4">
					<div class="flex items-center gap-2">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-blue-600">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
						</svg>
						<span class="text-sm font-medium">本周聊天进度</span>
					</div>
					{#if selectedModel}
						<div class="flex items-center gap-1.5 px-2 py-1 bg-blue-50 dark:bg-blue-900/20 rounded-md">
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-3.5 h-3.5 text-blue-600">
								<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
							</svg>
							<span class="text-xs text-blue-700 dark:text-blue-300">{selectedModel.split('/').pop()}</span>
						</div>
					{/if}
				</div>
				<div class="text-sm">
					<span class="font-semibold {isTargetMet ? 'text-green-600' : 'text-gray-900 dark:text-white'}">
						{formatTime(totalDuration)}
					</span>
					<span class="text-gray-500 dark:text-gray-400"> / {formatTime(weeklyTarget)}</span>
					{#if sessionDuration > 0}
						<span class="ml-2 text-xs text-blue-600">(本次: {formatTime(sessionDuration)})</span>
					{/if}
				</div>
			</div>

			<!-- 进度条 -->
			<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
				<div
					class="h-2 rounded-full transition-all duration-300 {isTargetMet ? 'bg-green-500' : 'bg-blue-600'}"
					style="width: {progress}%"
				></div>
			</div>

			{#if isTargetMet}
				<p class="text-xs text-green-600 mt-1">本周目标已完成！</p>
			{/if}
		</div>
	</div>

	<!-- 快捷情绪选择 -->
	<div class="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700 p-3">
		<div class="max-w-4xl mx-auto">
			<p class="text-xs text-gray-500 dark:text-gray-400 mb-2">快速选择你的感受:</p>
			<div class="flex gap-2 flex-wrap">
				<button
					on:click={() => selectMood('很开心')}
					class="px-3 py-1 text-sm bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400 rounded-full hover:bg-yellow-200 dark:hover:bg-yellow-900/50 transition"
				>
					开心
				</button>
				<button
					on:click={() => selectMood('平静')}
					class="px-3 py-1 text-sm bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 rounded-full hover:bg-blue-200 dark:hover:bg-blue-900/50 transition"
				>
					平静
				</button>
				<button
					on:click={() => selectMood('有点焦虑')}
					class="px-3 py-1 text-sm bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400 rounded-full hover:bg-orange-200 dark:hover:bg-orange-900/50 transition"
				>
					焦虑
				</button>
				<button
					on:click={() => selectMood('有些低落')}
					class="px-3 py-1 text-sm bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600 transition"
				>
					低落
				</button>
				<button
					on:click={() => selectMood('压力很大')}
					class="px-3 py-1 text-sm bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 rounded-full hover:bg-red-200 dark:hover:bg-red-900/50 transition"
				>
					压力大
				</button>
			</div>
		</div>
	</div>

	<!-- 聊天区域 -->
	<div bind:this={chatContainer} class="flex-1 overflow-y-auto p-4 bg-gray-50 dark:bg-gray-900">
		<div class="max-w-4xl mx-auto space-y-4">
			{#each messages as message}
				<div class="flex {message.role === 'user' ? 'justify-end' : 'justify-start'}">
					<div class="max-w-[80%] {message.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white'} rounded-lg p-4 shadow-sm">
						{message.content}
					</div>
				</div>
			{/each}

			{#if isLoading}
				<div class="flex justify-start">
					<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
						<div class="flex gap-1">
							<div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
							<div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
							<div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>

	<!-- 输入区域 -->
	<div class="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-4">
		<div class="max-w-4xl mx-auto">
			<form on:submit|preventDefault={sendMessage} class="flex gap-2">
				<input
					type="text"
					bind:value={inputMessage}
					on:keydown={handleKeydown}
					placeholder="分享你的感受..."
					class="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent dark:bg-gray-700 dark:text-white"
					disabled={isLoading}
				/>
				<button
					type="submit"
					disabled={isLoading || !inputMessage.trim()}
					class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition"
				>
					发送
				</button>
			</form>
			<p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
				提示：这是一个安全的空间，你可以自由地表达你的想法和感受。
			</p>
		</div>
	</div>
</div>
