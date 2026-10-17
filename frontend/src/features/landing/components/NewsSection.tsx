"use client";

import Image from "next/image";
import { useLocale } from "@/features/shared/context/LocaleContext";

const NEWS = [
  {
    image: "/images/news/vf9.jpg",
    title: "VinFast chính thức bàn giao xe VF 9 cho khách hàng",
    titleEn: "VinFast delivers the first VF 9 vehicles to customers",
    url: "https://vinfastauto.com/vn_vi/vinfast-chinh-thuc-ban-giao-xe-vf-9-cho-khach-hang",
  },
  {
    image: "/images/news/electric-scooters.png",
    title: "VinFast ra mắt 5 mẫu xe máy điện thế hệ mới sử dụng pin LFP",
    titleEn: "VinFast introduces five new electric scooters with LFP batteries",
    url: "https://vinfastauto.com/vn_vi/ve-chung-toi",
  },
  {
    image: "/images/news/ces-2022.png",
    title: "VinFast công bố chiến lược thuần điện tại CES 2022",
    titleEn: "VinFast announces its all-electric strategy at CES 2022",
    url: "https://vinfastauto.com/vn_vi/ve-chung-toi",
  },
  {
    image: "/images/news/vf-e34.png",
    title: "VinFast VF e34 chính thức ra mắt với nhiều tính năng thông minh",
    titleEn: "VinFast launches the VF e34 with smart features",
    url: "https://vinfastauto.com/vn_vi/ve-chung-toi",
  },
];

export function NewsSection() {
  const { language } = useLocale();
  const isEnglish = language === "en";

  return (
    <section id="news" aria-labelledby="news-heading" className="border-t border-slate-200/80 bg-white py-14 sm:py-16 scroll-mt-20">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <h2 id="news-heading" className="mb-8 text-center text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
          {isEnglish ? "News" : "Tin tức"}
        </h2>
        <div className="grid grid-cols-1 gap-x-7 gap-y-8 sm:grid-cols-2 lg:grid-cols-4">
          {NEWS.map((item) => (
            <article key={item.image}>
              <a href={item.url} target="_blank" rel="noopener noreferrer" className="group block rounded-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-service-primary">
                <div className="aspect-square overflow-hidden rounded-xl bg-slate-100">
                  <Image src={item.image} alt="" width={480} height={480} sizes="(min-width: 1152px) 251px, (min-width: 1024px) 23vw, (min-width: 640px) 46vw, 92vw" className="h-full w-full object-cover" />
                </div>
                <h3 className="mt-4 text-sm font-medium leading-relaxed text-slate-700 transition-colors group-hover:text-service-primary group-focus-visible:text-service-primary">
                  {isEnglish ? item.titleEn : item.title}
                  <span className="sr-only">{isEnglish ? " (opens in a new tab)" : " (mở trong thẻ mới)"}</span>
                </h3>
              </a>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
