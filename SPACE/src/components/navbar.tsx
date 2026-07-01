'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  navigationMenuTriggerStyle,
} from '@/components/ui/navigation-menu';

export function Navbar() {
  const pathname = usePathname();

  const links = [
    { href: '/', label: 'Candidates' },
    { href: '/map', label: 'Star Map' },
    { href: '/about', label: 'About' },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 h-16 bg-[#1e293b] border-b border-slate-700 flex items-center justify-between px-6 z-50">
      <div className="font-semibold text-lg text-slate-100">
        Exoplanet Pipeline
      </div>
      <NavigationMenu>
        <NavigationMenuList>
          {links.map((link) => {
            const isActive = pathname === link.href;
            return (
              <NavigationMenuItem key={link.href}>
                <Link href={link.href} legacyBehavior passHref>
                  <NavigationMenuLink
                    className={`${navigationMenuTriggerStyle()} bg-transparent hover:bg-slate-800 focus:bg-slate-800 ${
                      isActive ? 'text-[#f59e0b] underline underline-offset-4 decoration-2' : 'text-slate-300'
                    }`}
                  >
                    {link.label}
                  </NavigationMenuLink>
                </Link>
              </NavigationMenuItem>
            );
          })}
        </NavigationMenuList>
      </NavigationMenu>
    </nav>
  );
}
