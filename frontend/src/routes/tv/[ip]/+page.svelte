<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import Card from "$lib/components/ui/card/card.svelte";
  import Button from "$lib/components/ui/button/button.svelte";
  import Alert from "$lib/components/ui/alert/alert.svelte";
  import { tvService } from "$lib/services/tvService";
  import type { TVStatus } from "$lib/services/tvService";
  import {
    Tv,
    LoaderCircle,
    ArrowLeft,
    Power,
    PowerOff,
    Image as ArtIcon,
    BadgeCheck,
    BadgeX,
    Monitor,
    Trash2,
    Upload,
    Shuffle,
  } from "lucide-svelte";
  import { get } from "svelte/store";
  import Toggle from "$lib/components/ui/toggle/toggle.svelte";
  import PowerToggle from "$lib/components/PowerToggle.svelte";
  import ArtModeToggle from "$lib/components/ArtModeToggle.svelte";
  import DeleteImagesButton from "$lib/components/DeleteImagesButton.svelte";
  import Input from "$lib/components/ui/input/input.svelte";

  let ip = "";
  let tv: TVStatus | null = null;
  let loading = true;
  let error = "";
  let actionLoading = false;
  let actionError = "";
  let powerPressed = false;
  let artModePressed = false;
  let powerLoading = false;
  let artModeLoading = false;
  let deletingImages = false;
  let uploadingImages = false;
  let powerHover = false;
  let powerActionType: "on" | "off" | null = null;
  let artModeActionType: "on" | "off" | null = null;
  let successMessage = "";
  let showSuccess = false;
  let showDeleteConfirmation = false;
  let isActionInProgress = false;
  let slideshowStatus = {
    category: 0,
    duration: 0,
    running: false,
    shuffle: false,
  };

  $: if (tv) {
    powerPressed = tv.tv_on;
    artModePressed = tv.art_mode;
  }
  let prevPower = powerPressed;
  let prevArt = artModePressed;
  $: if (tv && powerPressed !== prevPower) {
    prevPower = powerPressed;
    if (powerPressed !== tv.tv_on) togglePower();
  }
  $: if (tv && artModePressed !== prevArt) {
    prevArt = artModePressed;
    if (artModePressed !== tv.art_mode) toggleArtMode();
  }

  $: isActionInProgress =
    powerLoading || artModeLoading || uploadingImages || deletingImages;

  onMount(async () => {
    ip = get(page).params.ip;
    await fetchTV();
  });

  async function fetchTV() {
    loading = true;
    error = "";
    try {
      const response = await tvService.getTVStatus(ip);
      tv = response.status;
      slideshowStatus = response.slideshow_status;
    } catch (e) {
      error = e instanceof Error ? e.message : "Erreur inconnue";
    } finally {
      loading = false;
    }
  }

  async function togglePower() {
    if (!tv) return;
    powerActionType = tv.tv_on ? "off" : "on";
    powerLoading = true;
    actionError = "";
    try {
      await tvService.powerControl(ip, tv.tv_on ? "off" : "on");
      await fetchTV();
    } catch (e) {
      actionError = e instanceof Error ? e.message : "Erreur action power";
    } finally {
      powerLoading = false;
      powerActionType = null;
    }
  }

  async function toggleArtMode() {
    if (!tv) return;
    artModeActionType = tv.art_mode ? "off" : "on";
    artModeLoading = true;
    actionError = "";
    try {
      await tvService.artMode(ip, tv.art_mode ? "off" : "on");
      await fetchTV();
    } catch (e) {
      actionError = e instanceof Error ? e.message : "Erreur action art mode";
    } finally {
      artModeLoading = false;
      artModeActionType = null;
    }
  }

  async function deleteAllImages() {
    showDeleteConfirmation = true;
  }

  async function confirmDeleteAllImages() {
    showDeleteConfirmation = false;
    deletingImages = true;
    actionError = "";
    try {
      await tvService.deleteAllArtImages(ip);
      successMessage = "Toutes les images ont été supprimées avec succès";
      showSuccess = true;
    } catch (e) {
      actionError =
        e instanceof Error
          ? e.message
          : "Erreur lors de la suppression des images";
    } finally {
      deletingImages = false;
    }
  }

  async function uploadFolderImages() {
    uploadingImages = true;
    actionError = "";
    try {
      const result = await tvService.uploadFolderImages(ip);
      const successCount = result.filter((r: any) => r.success).length;
      const errorCount = result.filter((r: any) => !r.success).length;
      successMessage = `${successCount} image(s) téléchargée(s) avec succès${errorCount > 0 ? `\n${errorCount} erreur(s)` : ""}`;
      showSuccess = true;
    } catch (e) {
      actionError =
        e instanceof Error
          ? e.message
          : "Erreur lors du téléchargement des images";
    } finally {
      uploadingImages = false;
    }
  }

  async function startCustomSlideshow() {
    if (!tv) return;
    actionLoading = true;
    actionError = "";
    try {
      await tvService.startCustomSlideshow(
        ip,
        slideshowStatus.duration,
        slideshowStatus.shuffle,
      );
      await fetchTV();
    } catch (e) {
      actionError =
        e instanceof Error
          ? e.message
          : "Erreur lors du démarrage du diaporama";
    } finally {
      actionLoading = false;
    }
  }

  async function stopCustomSlideshow() {
    if (!tv) return;
    actionLoading = true;
    actionError = "";
    try {
      await tvService.stopCustomSlideshow(ip);
      await fetchTV();
    } catch (e) {
      actionError =
        e instanceof Error ? e.message : "Erreur lors de l'arrêt du diaporama";
    } finally {
      actionLoading = false;
    }
  }

  function goBack() {
    goto("/");
  }
</script>

<div
  class="min-h-screen bg-gray-50 flex flex-col items-center py-8 px-4 sm:py-12 sm:px-0"
>
  <div class="w-full max-w-xl">
    <Button
      variant="ghost"
      size="sm"
      class="mb-3 sm:mb-4 flex items-center gap-2"
      on:click={goBack}
    >
      <ArrowLeft class="w-4 h-4" /> Back
    </Button>
    <Card class="p-4 sm:p-8 bg-white shadow-md rounded-xl">
      {#if loading}
        <div class="flex justify-center my-6 sm:my-8">
          <LoaderCircle
            class="animate-spin w-6 h-6 sm:w-8 sm:h-8 text-gray-400"
          />
        </div>
      {:else if error}
        <Alert variant="destructive" class="mb-4">{error}</Alert>
      {:else if tv}
        <div class="flex items-center gap-3 sm:gap-4 mb-4 sm:mb-6">
          <Tv class="w-10 h-10 sm:w-14 sm:h-14 text-gray-400" />
          <div>
            <div class="text-lg sm:text-2xl font-bold">
              {tv.raw_device_info.device.name}
            </div>
            <div class="text-gray-500 text-xs sm:text-sm">
              {tv.raw_device_info.device.modelName} · {tv.raw_device_info.device
                .ip}
            </div>
          </div>
        </div>
        <div class="flex flex-col gap-3 sm:gap-4">
          <div
            class="w-full {isActionInProgress && !powerLoading
              ? 'opacity-50 pointer-events-none'
              : ''}"
          >
            <PowerToggle
              tvOn={!!tv?.tv_on}
              loading={powerLoading}
              actionType={powerActionType}
              disabled={isActionInProgress && !powerLoading}
              on:toggle={togglePower}
            />
          </div>
          <div
            class="w-full {isActionInProgress && !artModeLoading
              ? 'opacity-50 pointer-events-none'
              : ''}"
          >
            <ArtModeToggle
              artOn={!!tv?.art_mode}
              loading={artModeLoading}
              actionType={artModeActionType}
              disabled={isActionInProgress && !artModeLoading}
              on:toggle={toggleArtMode}
            />
          </div>
          <div
            class="w-full {isActionInProgress && !uploadingImages
              ? 'opacity-50 pointer-events-none'
              : ''}"
          >
            <Button
              variant="default"
              class="w-full flex items-center justify-center gap-2"
              disabled={isActionInProgress && !uploadingImages}
              on:click={uploadFolderImages}
            >
              <Upload class="w-4 h-4" />
              {uploadingImages ? "Uploading..." : "Upload folder images"}
            </Button>
          </div>
          <div
            class="w-full {isActionInProgress && !deletingImages
              ? 'opacity-50 pointer-events-none'
              : ''}"
          >
            <DeleteImagesButton
              loading={deletingImages}
              disabled={isActionInProgress && !deletingImages}
              on:click={deleteAllImages}
            />
          </div>
          <h2 class="text-lg font-bold mt-8">Custom slideshow</h2>
          <div class="flex items-center gap-4">
            <div class="flex items-center gap-2">
              <label for="duration" class="text-sm">Interval (seconds):</label>
              <Input
                type="number"
                id="duration"
                bind:value={slideshowStatus.duration}
                min="1"
                class="border rounded p-1 w-20"
              />
            </div>
            <div class="flex items-center gap-2">
              <Toggle bind:pressed={slideshowStatus.shuffle}>
                <Shuffle class="w-5 h-5 text-gray-500" />
              </Toggle>
            </div>
          </div>
          <div
            class="w-full {isActionInProgress
              ? 'opacity-50 pointer-events-none'
              : ''}"
          >
            <Button
              variant="default"
              class="w-full flex items-center justify-center gap-2"
              disabled={isActionInProgress}
              on:click={startCustomSlideshow}
            >
              {slideshowStatus.running
                ? "Restart Slideshow"
                : "Start Slideshow"}
            </Button>
          </div>
          <div
            class="w-full {isActionInProgress
              ? 'opacity-50 pointer-events-none'
              : ''}"
          >
            <Button
              variant="default"
              class="w-full flex items-center justify-center gap-2"
              disabled={isActionInProgress || !slideshowStatus.running}
              on:click={stopCustomSlideshow}
            >
              Stop Slideshow
            </Button>
          </div>
        </div>

        {#if actionError}
          <Alert variant="destructive" class="mt-4">{actionError}</Alert>
        {/if}

        {#if showSuccess}
          <Alert variant="default" class="mt-4">{successMessage}</Alert>
        {/if}

        {#if showDeleteConfirmation}
          <Alert variant="destructive" class="mt-4">
            Êtes-vous sûr de vouloir supprimer toutes les images ?
            <div class="mt-2 flex gap-2">
              <Button
                variant="destructive"
                size="sm"
                on:click={confirmDeleteAllImages}>Confirmer</Button
              >
              <Button
                variant="outline"
                size="sm"
                on:click={() => (showDeleteConfirmation = false)}
                >Annuler</Button
              >
            </div>
          </Alert>
        {/if}
      {/if}
    </Card>
  </div>
</div>

<style>
  .animate-spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    100% {
      transform: rotate(360deg);
    }
  }

  :global(button:disabled),
  :global(.disabled) {
    opacity: 0.5 !important;
    cursor: not-allowed !important;
  }
</style>
