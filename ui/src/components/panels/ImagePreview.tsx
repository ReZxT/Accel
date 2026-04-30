interface Props {
  src: string
}

export default function ImagePreview({ src }: Props) {
  return (
    <div className="flex-1 flex items-center justify-center p-4 overflow-auto">
      <img
        src={src}
        alt="Preview"
        className="max-w-full max-h-full rounded-md object-contain"
      />
    </div>
  )
}
