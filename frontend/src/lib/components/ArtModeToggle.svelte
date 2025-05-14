<script lang="ts">
  import { Image as ArtIcon } from 'lucide-svelte';
  import { createEventDispatcher } from 'svelte';

  export let artOn: boolean;
  export let loading: boolean;
  export let actionType: 'on' | 'off' | null = null; // 'on' si on active, 'off' si on désactive
  export let disabled: boolean = false;

  const dispatch = createEventDispatcher();
  let hover = false;

  // Variables locales pour le style
  let artClass = '';
  let artStyle = '';
  let artText = '';
  let artIconColor = '';

  $: {
    let border = '';
    let bg = '';
    let text = '';
    let iconColor = '';
    let style = '';
    let animate = '';

    if (loading) {
      if (actionType === 'on') {
        border = 'border-blue-700 border';
        bg = '!bg-blue-700 !text-white';
        text = 'Art mode ...';
        iconColor = '!text-white';
        style = 'background-color:#1d4ed8;color:#fff;';
        animate = 'animate-pulse';
      } else {
        border = 'border-gray-700 border';
        bg = '!bg-gray-700 !text-white';
        text = 'Normal mode ...';
        iconColor = '!text-white';
        style = 'background-color:#334155;color:#fff;';
        animate = 'animate-pulse';
      }
    } else if (!artOn && hover) {
      border = 'border-blue-600 border';
      bg = 'bg-blue-50 text-blue-700';
      text = 'Enable art ?';
      iconColor = '!text-blue-700';
      style = 'background-color:#eff6ff;color:#1d4ed8;';
      animate = 'cursor-pointer';
    } else if (!artOn) {
      border = 'border-gray-400 border';
      bg = 'bg-gray-100 text-gray-600';
      text = 'Normal mode';
      iconColor = '!text-gray-500';
      style = 'background-color:#f3f4f6;color:#64748b;';
      animate = 'cursor-pointer';
    } else if (artOn && hover) {
      border = 'border-gray-700 border';
      bg = 'bg-gray-100 text-gray-700';
      text = 'Normal mode ?';
      iconColor = '!text-gray-700';
      style = 'background-color:#f3f4f6;color:#334155;';
      animate = 'cursor-pointer';
    } else if (artOn) {
      border = '!bg-blue-700 !text-white';
      bg = '';
      text = 'Art Mode ON';
      iconColor = '!text-white';
      style = 'background-color:#1d4ed8;color:#fff;';
      animate = 'cursor-pointer';
    }

    // Bordure transparente par défaut si aucune bordure colorée n'est définie
    if (!border.includes('border-')) {
      border = 'border border-transparent ' + border;
    }

    artClass = `flex w-full items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background ${border} ${bg} shadow ${animate}`;
    artStyle = style;
    artText = text;
    artIconColor = iconColor;
  }
</script>

<button
  type="button"
  {disabled}
  aria-disabled={disabled}
  on:mouseenter={() => hover = true}
  on:mouseleave={() => hover = false}
  class={artClass}
  style={artStyle}
  on:click={() => !disabled && dispatch('toggle')}
>
  <ArtIcon class={`w-4 h-4 ${artIconColor}`} />
  <span class={`font-semibold ${loading ? '!text-white' : ''}`}>{artText}</span>
</button> 