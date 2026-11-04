export function classify(labels, scores, threshold) {
  let tp=0, fp=0, tn=0, fn=0;
  labels.forEach((actual,i) => { const positive=scores[i]>=threshold; if(actual) positive?tp++:fn++; else positive?fp++:tn++; });
  const precision=tp+fp?tp/(tp+fp):0, recall=tp+fn?tp/(tp+fn):0;
  return {tp,fp,tn,fn,precision,recall,f1:2*tp+fp+fn?2*tp/(2*tp+fp+fn):0,accuracy:(tp+tn)/labels.length};
}
