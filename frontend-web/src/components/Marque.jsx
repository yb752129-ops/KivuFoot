import { Ballon } from "../icons.jsx";

/** KivuF[ballon]t — le o de Foot est le sceau, pas un emoji. */
export default function Marque() {
  return (
    <>
      <span className="wordmark-name">
        KivuF
        <span className="wordmark-o">
          <Ballon />
        </span>
        t
      </span>
      <span className="wordmark-place">Sud-Kivu</span>
    </>
  );
}
